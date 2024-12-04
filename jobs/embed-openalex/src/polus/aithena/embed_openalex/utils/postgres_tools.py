
from functools import wraps
from pathlib import Path
from typing import Any, Callable
from dotenv import load_dotenv
import psycopg_pool
from openalex_types.works import Work
from polus.aithena.common.utils import async_time_logger
from polus.aithena.common.logger import get_logger
from polus.aithena.embed_openalex.config import EMBEDDING_TABLE

logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

POOL: psycopg_pool.AsyncConnectionPool = None

async def get_async_pool_singleton(
        conn_info: str = None,
        db_max_connections: int = 4,
        db_min_connections : int = 1,
        timeout : int = 300
    ) -> psycopg_pool.AsyncConnectionPool:
    """Get a connection pool for async operations."""
    global POOL
    if POOL is None:
        if conn_info is None:
            raise ValueError("Connection info must be provided to create a new pool.")
        POOL = psycopg_pool.AsyncConnectionPool(
            conn_info,
            open=False,
            max_size=db_max_connections,
            min_size=db_min_connections,
            timeout=timeout
        )
        await POOL.open(wait=True)
    return POOL

async def get_async_pool(
        conn_info: str ,
        db_max_connections: None,
        db_min_connections : int = 4,
        timeout=300
    ) -> psycopg_pool.AsyncConnectionPool:
    """Get a connection pool for async operations."""
    pool = psycopg_pool.AsyncConnectionPool(
        conn_info,
        open=False,
        max_size=db_max_connections,
        min_size=db_min_connections,
        timeout=timeout
    )
    await pool.open(wait=True)
    return pool

def get_pool(
        conn_info: str ,
        db_max_connections: int,
        db_min_connections : int = 4
    ) -> psycopg_pool.ConnectionPool:
    """Get a connection pool for async operations."""
    return psycopg_pool.ConnectionPool(
        conn_info,
        open=False,
        max_size=db_max_connections,
        min_size=db_min_connections,
    )

async def async_query(pool: psycopg_pool.ConnectionPool, query: str):
    """Execute a query asynchronously and return the results."""
    # logger.debug("Attempt to create connection")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query)
            results = await cur.fetchall()
            return results
        # TODO CHECK cost of commiting after each query
        # conn.commit()

def sync_query(pool: psycopg_pool.ConnectionPool, query: str):
    """Execute a query asynchronously and return the results."""
    # logger.debug("Attempt to create connection")
    with pool.connection() as conn:
        # logger.debug("Connected to database")
        with conn.cursor() as cur:
            # logger.debug("Created cursor")
            cur.execute(query)
            # logger.debug("Executed query")
            results = cur.fetchall()
            return results
        # TODO CHECK cost
        conn.commit()

def sync_get_works_count(pool):
    """Get the total amount of works in the database."""
    schema_name = "openalex"
    table_name = "works"
    count_works_query = f"""
        SELECT COUNT(*)
        FROM {schema_name}.{table_name}
    """
    res = sync_query(pool, count_works_query)
    total_work_count = res[0][0]
    # logger.debug(f"Total amount of works: {total_work_count}")
    return total_work_count

@async_time_logger
async def get_works_count(pool):
    """Get the total amount of works in the database."""
    schema_name = "openalex"
    table_name = "works"
    count_works_query = f"""
        SELECT COUNT(*)
        FROM {schema_name}.{table_name}
    """
    res = await async_query(pool, count_works_query)
    total_work_count = res[0][0]
    # logger.debug(f"Total amount of works: {total_work_count}")
    return total_work_count

# @async_time_logger
# async def get_works(pool, offset, batch_size):
#     schema_name = "openalex"
#     table_name = "works"
#     works_query = f"""
#         SELECT *
#         FROM {schema_name}.{table_name}
#         ORDER BY id
#         OFFSET {offset}
#         LIMIT {batch_size}
#     """
#     res = await async_query(pool, works_query)
#     works = [Work.from_sql(work) for work in res]
#     assert len(works) == batch_size, f"Expected {batch_size} works, got {len(works)}"
#     return works

@async_time_logger
async def get_works(pool, offset, batch_size):
    """Get a batch of works from the database.
    
    This implementation relies on a separate index table to get the works in a specific order.
    This vastly improves performance compared to the naive implementation.
    """
    schema_name = "openalex"
    table_name = "works"
    works_query = f"""
        SELECT *
        FROM {schema_name}.{table_name}
        INNER JOIN (
        SELECT {schema_name}.index_works.id FROM {schema_name}.index_works WHERE row_number >= {offset}
        AND row_number < {offset + batch_size}
        )
        indexes ON openalex.works.id = indexes.id;
    """
    res = await async_query(pool, works_query)
    works = [Work.from_sql(work) for work in res]
    assert len(works) == batch_size, f"At offset {offset}, Expected {batch_size} works, got {len(works)}"
    work_ids = [work.id for work in works]
    # logger.debug(f"Work ids: {work_ids} for offset {offset}")
    return works