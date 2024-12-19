# mypy: disable-error-code="import-untyped"
# pylint: disable=E1129, W1203
"""pgvector database utilities for aithena-services."""
import re

import psycopg
from aithena_services.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from openalex_types import Work
from polus.aithena.common.logger import get_logger

logger = get_logger("aithena_services.memory.pgvector")

DB_CONFIG_STRING = f"dbname={POSTGRES_DB} user={POSTGRES_USER} "
DB_CONFIG_STRING += f"port={POSTGRES_PORT} host={POSTGRES_HOST} password={POSTGRES_PASSWORD}"

def similarity_search(
    table_name: str,
    vector: list[float],
    limit: int,
) -> list[Work]:
    """
    Search for similar vectors in a table.

    Args:
        table_name (str): The name of the table to search in.
        vector_column (str): The name of the column containing the vectors.
        return_column (str): The name of the column to return in the results.
        vector (list[float]): The vector to search for similarities.
        limit (int, optional): The maximum number of similar vectors to return.

    Returns:
        list[str]: A list of IDs of the similar vectors found.
    """
    query = f"""
    WITH limited_works AS (
    SELECT works.id
    FROM {table_name} AS emb
    JOIN openalex.works AS works
        ON emb.work_id = works.id
    ORDER BY emb.embedding <=> '{vector}'
    LIMIT {limit}
    )
    SELECT
        row_to_json(works)::jsonb || jsonb_build_object(
            'authorships',
            CASE
                WHEN COUNT(works_authorships.work_id) = 0 THEN NULL
                ELSE json_agg(
                    DISTINCT json_build_object(
                        'author', json_build_object(
                            'display_name', authors.display_name,
                            'id', works_authorships.author_id
                        )::jsonb
                    )::jsonb
                )
            END
        ) AS work_with_authorships
    FROM limited_works
    JOIN openalex.works AS works
        ON limited_works.id = works.id
    LEFT JOIN openalex.works_authorships AS works_authorships
        ON works.id = works_authorships.work_id
    LEFT JOIN openalex.authors AS authors
        ON works_authorships.author_id = authors.id
    GROUP BY works.id;  
    """

    with psycopg.connect(DB_CONFIG_STRING) as conn:
        with conn.cursor() as cur:
            try:
                query_to_log = re.sub(r"\[.*?\]", "[...]", query)
                logger.debug(
                    f"Performing similarity search with query: {query_to_log}")
                cur.execute(query)
                res = cur.fetchall()

                print("!!!!!!!!!!!! res", res)

                works = [Work(**w[0]) for w in res]
            except Exception as e:
                logger.error(f"Error when performing similarity search: {e}")
                raise e

    return works

def work_ids_by_similarity_search(
    table_name: str,
    vector: list[float],
    limit: int,
) -> list[Work]:
    """
    Search for similar vectors in a table.

    Args:
        table_name (str): The name of the table to search in.
        vector (list[float]): The vector to search for similarities.
        limit (int, optional): The maximum number of similar vectors to return.

    Returns:
        list[str]: A list of IDs of the similar vectors found.
    """
    query = f"""
SELECT work_id
FROM {table_name}
ORDER BY embedding <=> '{vector}' LIMIT {limit};
    """

    with psycopg.connect(DB_CONFIG_STRING) as conn:
        with conn.cursor() as cur:
            try:
                query_to_log = re.sub(r"\[.*?\]", "[...]", query)
                logger.debug(
                    f"Performing similarity search with query: {query_to_log}")
                cur.execute(query)
                res = cur.fetchall()
            except Exception as e:
                logger.error(f"Error when performing similarity search: {e}")
                raise e

    return res

def works_by_similarity_search(
    table_name: str,
    vector: list[float],
    limit: int,
) -> list[Work]:
    """
    Search for similar vectors in a table.

    Args:
        table_name (str): The name of the table to search in.
        vector (list[float]): The vector to search for similarities.
        limit (int, optional): The maximum number of similar vectors to return.

    Returns:
        list[str]: A list of IDs of the similar vectors found.
    """
    query = f"""
WITH selected_work_ids AS (
SELECT work_id
FROM {table_name}
ORDER BY embedding <=> '{vector}' LIMIT {limit}
)
SELECT w.*
FROM openalex.works w
JOIN selected_work_ids s ON w.id = s.work_id;
;
    """

    with psycopg.connect(DB_CONFIG_STRING) as conn:
        with conn.cursor() as cur:
            try:
                query_to_log = re.sub(r"\[.*?\]", "[...]", query)
                logger.debug(
                    f"Performing similarity search with query: {query_to_log}")
                cur.execute(query)
                res = cur.fetchall()
                works = [Work.from_sql(work) for work in res]
            except Exception as e:
                logger.error(f"Error when performing similarity search: {e}")
                raise e

    return works