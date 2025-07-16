"""Redis client for Ask Aithena with enhanced performance and reliability."""
import asyncio
from contextlib import asynccontextmanager
from typing import Any
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError
import orjson
from polus.aithena.ask_aithena.config import REDIS_URL
from polus.aithena.common.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    """
    A high-performance Redis client for caching session data.
    
    Features:
    - Connection pooling for better performance
    - orjson for faster JSON serialization (2-3x faster than standard json)
    - Automatic retry logic with exponential backoff
    - Context manager support for clean resource management
    - Pipeline support for batch operations
    - Health check capability
    """

    def __init__(
        self, 
        redis_url: str,
        max_connections: int = 50,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        max_retries: int = 3,
        retry_delay: float = 0.1
    ):
        """
        Initialize Redis client with connection pooling.
        
        Args:
            redis_url: Redis connection URL
            max_connections: Maximum number of connections in the pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connection timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self._redis_url = redis_url
        self._pool: ConnectionPool | None = None
        self._redis: redis.Redis | None = None
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        
        # Connection pool configuration
        self._pool_config = {
            "max_connections": max_connections,
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
            "retry_on_timeout": retry_on_timeout,
            "decode_responses": False,  # We'll handle decoding ourselves with orjson
        }
        
        logger.info(
            "Initialized RedisClient - max_connections: %d, socket_timeout: %.1f, max_retries: %d",
            max_connections, socket_timeout, max_retries
        )

    async def connect(self) -> None:
        """
        Establish a connection pool to Redis.
        
        Raises:
            ConnectionError: If unable to connect to Redis
        """
        try:
            self._pool = ConnectionPool.from_url(self._redis_url, **self._pool_config)
            self._redis = redis.Redis(connection_pool=self._pool)
            
            # Test the connection
            await self._redis.ping()
            logger.info("Successfully connected to Redis")
            
        except (ConnectionError, TimeoutError) as e:
            logger.error("Failed to connect to Redis: %s", e)
            raise ConnectionError(f"Unable to connect to Redis: {e}") from e

    async def disconnect(self) -> None:
        """Close the connection pool to Redis."""
        if self._pool:
            await self._pool.disconnect()
            logger.info("Disconnected from Redis")
        self._redis = None
        self._pool = None

    async def _execute_with_retry(self, operation, *args, **kwargs) -> Any:
        """
        Execute a Redis operation with retry logic.
        
        Args:
            operation: The Redis operation to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            The result of the operation
            
        Raises:
            RedisError: If all retry attempts fail
        """
        last_error = None
        delay = self._retry_delay
        
        for attempt in range(self._max_retries):
            try:
                return await operation(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    logger.warning(
                        "Redis operation failed (attempt %d/%d): %s",
                        attempt + 1, self._max_retries, e
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error("Redis operation failed after %d attempts: %s", self._max_retries, e)
        
        raise last_error

    async def set_json(self, key: str, data: dict | list, expiration: int | None = None) -> None:
        """
        Store a JSON-serializable object in Redis with optional expiration.
        
        Uses orjson for fast serialization with support for datetime, UUID, etc.
        
        Args:
            key: The key to store the data under
            data: The dictionary or list to store
            expiration: Optional expiration time in seconds
            
        Raises:
            RedisError: If unable to store the data
        """
        if not self._redis:
            raise ConnectionError("Redis client not connected")
        
        try:
            serialized = orjson.dumps(data)
            await self._execute_with_retry(
                self._redis.set,
                key,
                serialized,
                ex=expiration
            )
            logger.debug("Stored data for key: %s, expiration: %s", key, f"{expiration}s" if expiration else "None")
        except orjson.JSONEncodeError as e:
            logger.error("Failed to serialize data for key %s: %s", key, e)
            raise ValueError(f"Data is not JSON serializable: {e}") from e
        except RedisError as e:
            logger.error("Failed to store data for key %s: %s", key, e)
            raise

    async def get_json(self, key: str) -> dict | list | None:
        """
        Retrieve and deserialize a JSON object from Redis.
        
        Args:
            key: The key of the data to retrieve
            
        Returns:
            The deserialized object, or None if the key doesn't exist
            
        Raises:
            RedisError: If unable to retrieve the data
        """
        if not self._redis:
            raise ConnectionError("Redis client not connected")
        
        try:
            data = await self._execute_with_retry(self._redis.get, key)
            if data is None:
                logger.debug("Key not found: %s", key)
                return None
            
            deserialized = orjson.loads(data)
            logger.debug("Retrieved data for key: %s", key)
            return deserialized
            
        except orjson.JSONDecodeError as e:
            logger.error("Failed to deserialize data for key %s: %s", key, e)
            raise ValueError(f"Data is not valid JSON: {e}") from e
        except RedisError as e:
            logger.error("Failed to retrieve data for key %s: %s", key, e)
            raise

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from Redis.
        
        Args:
            *keys: Keys to delete
            
        Returns:
            Number of keys deleted
            
        Raises:
            RedisError: If unable to delete the keys
        """
        if not self._redis:
            raise ConnectionError("Redis client not connected")
        
        try:
            deleted = await self._execute_with_retry(self._redis.delete, *keys)
            logger.debug("Deleted %d key(s): %s", deleted, keys)
            return deleted
        except RedisError as e:
            logger.error("Failed to delete keys %s: %s", keys, e)
            raise

    async def exists(self, *keys: str) -> int:
        """
        Check if one or more keys exist.
        
        Args:
            *keys: Keys to check
            
        Returns:
            Number of keys that exist
            
        Raises:
            RedisError: If unable to check the keys
        """
        if not self._redis:
            raise ConnectionError("Redis client not connected")
        
        try:
            count = await self._execute_with_retry(self._redis.exists, *keys)
            return count
        except RedisError as e:
            logger.error("Failed to check existence of keys %s: %s", keys, e)
            raise

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time on a key.
        
        Args:
            key: The key to set expiration on
            seconds: Expiration time in seconds
            
        Returns:
            True if expiration was set, False if key doesn't exist
            
        Raises:
            RedisError: If unable to set expiration
        """
        if not self._redis:
            raise ConnectionError("Redis client not connected")
        
        try:
            result = await self._execute_with_retry(self._redis.expire, key, seconds)
            logger.debug("Set expiration for key %s: %ds", key, seconds)
            return result
        except RedisError as e:
            logger.error("Failed to set expiration for key %s: %s", key, e)
            raise

    def pipeline(self) -> redis.client.Pipeline:
        """
        Create a pipeline for batch operations.
        
        Pipelines reduce round trips by batching commands.
        
        Returns:
            A Redis pipeline object
            
        Example:
            async with client.pipeline() as pipe:
                pipe.set("key1", "value1")
                pipe.set("key2", "value2")
                pipe.get("key3")
                results = await pipe.execute()
        """
        if not self._redis:
            raise ConnectionError("Redis client not connected")
        
        return self._redis.pipeline()

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the Redis connection.
        
        Returns:
            Dictionary with health status and metadata
        """
        try:
            if not self._redis:
                return {
                    "status": "disconnected",
                    "error": "Redis client not connected"
                }
            
            # Ping Redis
            start = asyncio.get_event_loop().time()
            await self._redis.ping()
            latency_ms = (asyncio.get_event_loop().time() - start) * 1000
            
            # Get Redis info
            info = await self._redis.info()
            
            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_in_days": info.get("uptime_in_days", 0),
            }
            
        except Exception as e:
            logger.error("Health check failed: %s", e)
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for Redis transactions.
        
        Example:
            async with client.transaction() as pipe:
                await pipe.watch("key1")
                value = await pipe.get("key1")
                pipe.multi()
                pipe.set("key1", int(value) + 1)
                await pipe.execute()
        """
        if not self._redis:
            raise ConnectionError("Redis client not connected")
        
        pipe = self._redis.pipeline(transaction=True)
        try:
            yield pipe
        finally:
            await pipe.reset()

    def __repr__(self) -> str:
        """String representation of the RedisClient."""
        return f"RedisClient(url={self._redis_url}, connected={self._redis is not None})"


# Singleton instance with optimized settings for session storage
redis_client = RedisClient(
    REDIS_URL,
    max_connections=100,  # Increased for high concurrency
    socket_timeout=5.0,
    socket_connect_timeout=5.0,
    retry_on_timeout=True,
    max_retries=3,
    retry_delay=0.1
)


async def get_redis_client() -> RedisClient:
    """
    Get the singleton Redis client instance.
    
    This is used for FastAPI dependency injection.
    
    Returns:
        The Redis client instance
    """
    return redis_client
