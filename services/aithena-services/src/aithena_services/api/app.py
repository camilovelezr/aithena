# mypy: disable-error-code="import-untyped"
"""Aithena-Services FastAPI REST Endpoints. """

# pylint: disable=W1203, C0412, C0103, W0212, W0707, W0718

from aithena_services.memory.pgvector import (
    similarity_search,
    work_ids_by_similarity_search,
    works_by_similarity_search,
)
from fastapi import FastAPI, HTTPException
from polus.aithena.common.logger import get_logger
from polus.aithena.common.utils import time_logger
from pydantic import BaseModel

logger = get_logger("aithena_services.api")


app = FastAPI()


class VectorSearchRequest(BaseModel):
    table_name: str
    vector: list[float]
    n: int = 10
    full: bool = False


class WorkIdsSearchRequest(BaseModel):
    table_name: str
    vector: list[float]
    n: int = 10


class WorksSearchRequest(BaseModel):
    table_name: str
    vector: list[float]
    n: int = 10

@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        logger.info("Health check endpoint called")
        return {"status": "ok", "aithena-services": "running"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@time_logger
@app.post("/memory/pgvector/search")
def search_pgvector(request: VectorSearchRequest):
    """
    Search for similar vectors in a specified table using pgvector with cosine distance.

    Args:
        request (VectorSearchRequest): The search request containing:
            - table_name: The name of the table to search in
            - vector: The vector to search for similar vectors
            - n: The number of similar vectors to return (default: 10)
            - full: Whether to return the full Work object (default: False)

    Returns:
        The result of the similarity search as a list of Work objects.

    Raises:
        HTTPException: If there is an error during the similarity search.
    """
    try:
        res = similarity_search(
            request.table_name, request.vector, request.n, request.full
        )
    except Exception as exc:
        logger.error(f"Error in similarity search: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    return res


@time_logger
@app.post("/memory/pgvector/search_work_ids")
def search_work_ids_pgvector(request: WorkIdsSearchRequest):
    """
    Search for work IDs using pgvector similarity search.

    This function performs a similarity search on
    the specified table using the provided vector and returns the top `n` work IDs.

    Args:
        request (WorkIdsSearchRequest): The search request containing:
            - table_name: The name of the table to search in
            - vector: The vector to use for the similarity search
            - n: The number of top results to return (default: 10)

    Returns:
        list: A list of work IDs that are most similar to the provided vector.

    Raises:
        HTTPException: If an error occurs during the similarity search.
    """
    try:
        res = work_ids_by_similarity_search(
            request.table_name, request.vector, request.n
        )
    except Exception as exc:
        logger.error(f"Error in similarity search: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    return res


@time_logger
@app.post("/memory/pgvector/search_works")
def search_works_pgvector(request: WorksSearchRequest):
    """
    Perform a similarity search on the specified table using a vector.

    Args:
        request (WorksSearchRequest): The search request containing:
            - table_name: The name of the table to search
            - vector: The vector to use for the similarity search
            - n: The number of results to return (default: 10)

    Returns:
        list: The search results.

    Raises:
        HTTPException: If an error occurs during the similarity search.
    """
    try:
        res = works_by_similarity_search(request.table_name, request.vector, request.n)
    except Exception as exc:
        logger.error(f"Error in similarity search: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    return res
