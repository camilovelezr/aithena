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
    full: bool,
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
    # query = f"SELECT {return_column} FROM {table_name} "
    # query += f"ORDER BY embedding <=> '{vector}' LIMIT {limit};"
    query = f"""
    SELECT works.* 
    FROM {table_name} AS emb
    JOIN openalex.works AS works
    ON emb.work_id = works.id
    ORDER BY emb.embedding <=> '{vector}' 
    LIMIT {limit};
    """
    with psycopg.connect(DB_CONFIG_STRING) as conn:
        with conn.cursor() as cur:
            try:
                query_to_log = re.sub(r"\[.*?\]", "[...]", query)
                logger.debug(
                    f"Performing similarity search with query: {query_to_log}")
                cur.execute(query)
                res = cur.fetchall()
                if full:
                    works = [Work.from_sql(tup, conn) for tup in res]
                else:
                    works = [Work.from_sql(tup) for tup in res]
            except Exception as e:
                logger.error(f"Error when performing similarity search: {e}")
                raise e

    return works
