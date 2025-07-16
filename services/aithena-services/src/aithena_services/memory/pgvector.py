# mypy: disable-error-code="import-untyped"
# pylint: disable=E1129, W1203
"""pgvector database utilities for aithena-services."""
from typing import Optional

import asyncpg
import orjson
from aithena_services.config import (
    IVFFLAT_PROBES,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from polus.aithena.common.logger import get_logger

logger = get_logger("aithena_services.memory.pgvector")

# Connection pool - will be initialized at startup
_pool: Optional[asyncpg.Pool] = None


async def init_pool(
    min_size: int = 10,
    max_size: int = 20,
    max_queries: int = 50000,
    max_inactive_connection_lifetime: float = 300.0,
) -> asyncpg.Pool:
    """Initialize the connection pool."""
    global _pool
    
    if _pool is not None:
        logger.warning("Pool already initialized, closing existing pool")
        await close_pool()
    
    # Define connection setup function
    async def setup_connection(conn):
        # Set ivfflat probes if configured
        if IVFFLAT_PROBES:
            await conn.execute(f'SET ivfflat.probes = {IVFFLAT_PROBES}')
            logger.debug(f"Set ivfflat.probes = {IVFFLAT_PROBES}")
    
    logger.info(f"Initializing asyncpg connection pool to {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    
    _pool = await asyncpg.create_pool(
        host=POSTGRES_HOST,
        port=int(POSTGRES_PORT),
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        min_size=min_size,
        max_size=max_size,
        max_queries=max_queries,
        max_inactive_connection_lifetime=max_inactive_connection_lifetime,
        command_timeout=60,
        statement_cache_size=100,  # Cache prepared statements
        setup=setup_connection,  # Set up each connection with ivfflat.probes
        server_settings={
            'jit': 'off',  # Disable JIT for short queries
            'random_page_cost': '1.1',  # Optimized for SSD
        }
    )
    
    
    # Test the connection and log database info
    async with _pool.acquire() as conn:
        current_db = await conn.fetchval("SELECT current_database()")
        schemas = await conn.fetch("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema') ORDER BY schema_name")
        schema_list = [r['schema_name'] for r in schemas]
        
        logger.info(f"Connection pool initialized successfully")
        logger.info(f"Connected to database: {current_db}")
        logger.info(f"Available schemas: {schema_list}")
        if IVFFLAT_PROBES:
            logger.info(f"IVFFlat probes set to: {IVFFLAT_PROBES}")
        
        # Check if openalex schema exists and has the expected table
        if 'openalex' in schema_list:
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'openalex' 
                AND table_name LIKE '%embedding%'
                ORDER BY table_name
            """)
            table_list = [r['table_name'] for r in tables]
            logger.info(f"Embedding tables in openalex schema: {table_list}")
    
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Connection pool closed")


def get_pool() -> asyncpg.Pool:
    """Get the connection pool. Raises RuntimeError if pool not initialized."""
    if _pool is None:
        raise RuntimeError(
            "Connection pool not initialized. Call init_pool() first."
        )
    return _pool


def return_query_full_work(table_name: str, vector: list[float], limit: int) -> str:
    """Return query for full work."""
    query = f"""
    WITH limited_works AS (
    SELECT works.id
    FROM {table_name} AS emb
    JOIN openalex.works AS works
        ON emb.work_id = works.id
    ORDER BY emb.embedding <=> '{vector}'
    LIMIT {limit}
    ) --- CTE: do this first to limit the number of works
    SELECT
        jsonb_agg(
            jsonb_strip_nulls(
                row_to_json(works)::jsonb || jsonb_build_object(
                    'primary_location', (
                        SELECT row_to_json(works_primary_locations)::jsonb
                        FROM openalex.works_primary_locations AS works_primary_locations
                        WHERE works_primary_locations.work_id = works.id
                    ),
                    'locations', (
                        SELECT jsonb_agg(row_to_json(works_locations)::jsonb)
                        FROM openalex.works_locations AS works_locations
                        WHERE works_locations.work_id = works.id
                    ),
                    'best_oa_location', (
                        SELECT row_to_json(works_best_oa_location)::jsonb
                        FROM openalex.works_best_oa_locations AS works_best_oa_location
                        WHERE works_best_oa_location.work_id = works.id
                    ),
                    'authorships', (
                        SELECT jsonb_agg(row_to_json(works_authorships)::jsonb)
                        FROM openalex.works_authorships AS works_authorships
                        WHERE works_authorships.work_id = works.id
                    ),
                    'biblio', (
                        SELECT row_to_json(works_biblio)::jsonb
                        FROM openalex.works_biblio AS works_biblio
                        WHERE works_biblio.work_id = works.id
                    ),
                    'topics', (
                        SELECT jsonb_agg(row_to_json(works_topics)::jsonb)
                        FROM openalex.works_topics AS works_topics
                        WHERE works_topics.work_id = works.id
                    ),
                    'concepts', (
                        SELECT jsonb_agg(row_to_json(works_concepts)::jsonb)
                        FROM openalex.works_concepts AS works_concepts
                        WHERE works_concepts.work_id = works.id
                    ),
                    'ids', (
                        SELECT row_to_json(works_ids)::jsonb
                        FROM openalex.works_ids AS works_ids
                        WHERE works_ids.work_id = works.id
                    ),
                    'mesh', (
                        SELECT jsonb_agg(row_to_json(works_mesh)::jsonb)
                        FROM openalex.works_mesh AS works_mesh
                        WHERE works_mesh.work_id = works.id
                    ),
                    'open_access', (
                        SELECT row_to_json(works_open_access)::jsonb
                        FROM openalex.works_open_access AS works_open_access
                        WHERE works_open_access.work_id = works.id
                    ),
                    'referenced_works', (
                        SELECT jsonb_agg(row_to_json(works_referenced_works)::jsonb)
                        FROM openalex.works_referenced_works AS works_referenced_works
                        WHERE works_referenced_works.work_id = works.id
                    ),
                    'related_works', (
                        SELECT jsonb_agg(row_to_json(works_related_works)::jsonb)
                        FROM openalex.works_related_works AS works_related_works
                        WHERE works_related_works.work_id = works.id
                    )
                )
            )
        ) AS full_work
    FROM limited_works
    JOIN openalex.works AS works
        ON limited_works.id = works.id
    """
    return query


async def similarity_search(
    table_name: str,
    vector: list[float],
    limit: int,
    full: bool = False,
) -> list[dict]:
    """
    Search for similar works.

    If full is set to True, the full Work object is returned.
    If full is set to False, only the basic work metadata with
    authorships is returned.

    Args:
        table_name (str): The name of the table to search in.
        vector (list[float]): The vector to search for similarities.
        limit (int, optional): The maximum number of similar vectors to return.
        full (bool, optional): Whether to query and return the full Work object.

    Returns:
        list[dict]: A list of Work objects as dict.
    """
    # if not full:
    #     query = f"""
    #     WITH limited_works AS (
    #     SELECT works.id
    #     FROM {table_name} AS emb
    #     JOIN openalex.works AS works
    #         ON emb.work_id = works.id
    #     ORDER BY emb.embedding <=> '{vector}'
    #     LIMIT {limit}
    #     )
    #     SELECT
    #         row_to_json(works)::jsonb || jsonb_build_object(
    #             'authorships',
    #             CASE
    #                 WHEN COUNT(works_authorships.work_id) = 0 THEN NULL
    #                 ELSE json_agg(
    #                     DISTINCT json_build_object(
    #                         'author', json_build_object(
    #                             'display_name', authors.display_name,
    #                             'id', works_authorships.author_id
    #                         )::jsonb
    #                     )::jsonb
    #                 )
    #             END
    #         ) AS work_with_authorships
    #     FROM limited_works
    #     JOIN openalex.works AS works
    #         ON limited_works.id = works.id
    #     LEFT JOIN openalex.works_authorships AS works_authorships
    #         ON works.id = works_authorships.work_id
    #     LEFT JOIN openalex.authors AS authors
    #         ON works_authorships.author_id = authors.id
    #     GROUP BY works.id;  
    #     """
    raise NotImplementedError("Not implemented")


async def works_by_similarity_search(
    table_name: str,
    vector: list[float],
    limit: int,
) -> list[dict]:
    """
    Search for similar works and return just basic work metadata with authorships.
    Uses prepared statements and optimized query structure for better performance.

    Args:
        table_name (str): The name of the table to search in.
        vector (list[float]): The vector to search for similarities.
        limit (int, optional): The maximum number of similar vectors to return.

    Returns:
        list[dict]: A list of dicts containing the works data with authorships.
    """
    # Optimized query using LATERAL join
    query_template = f"""
    WITH selected_work_ids AS (
        SELECT work_id
        FROM {table_name}
        ORDER BY embedding <=> $1::vector LIMIT $2
    )
    SELECT 
        w.id,
        w.title,
        w.abstract,
        w.publication_year,
        w.doi,
        COALESCE(auth.authorships, '[]'::json) as authorships
    FROM selected_work_ids s
    JOIN openalex.works w ON w.id = s.work_id
    LEFT JOIN LATERAL (
        SELECT json_agg(
            json_build_object(
                'author_position', wa.author_position,
                'author_id', wa.author_id,
                'display_name', a.display_name
            ) ORDER BY wa.author_position
        ) as authorships
        FROM openalex.works_authorships wa
        JOIN openalex.authors a ON wa.author_id = a.id
        WHERE wa.work_id = w.id
    ) auth ON true;
    """

    pool = get_pool()
    async with pool.acquire() as conn:
        try:
            # Prepare statement for this connection
            logger.debug(f"Preparing statement for table: {table_name}")
            prepared_stmt = await conn.prepare(query_template)
            
            # Convert vector to string format for PostgreSQL
            vector_str = f"[{','.join(map(str, vector))}]"
            
            # Execute prepared statement
            rows = await prepared_stmt.fetch(vector_str, limit)
            
            # Convert asyncpg Records to dicts with proper handling of None values
            results = []
            for row in rows:
                result = {
                    'id': row['id'],
                    'title': row['title'],
                    'abstract': row['abstract'],
                    'publication_year': row['publication_year'],
                    'doi': row['doi'],
                    'authorships': orjson.loads(row['authorships']) if row['authorships'] else []
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error when performing similarity search: {e}")
            raise e
