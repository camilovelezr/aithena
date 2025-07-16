# mypy: disable-error-code="import-untyped"
"""Aithena-Services FastAPI REST Endpoints. """

# pylint: disable=W1203, C0412, C0103, W0212, W0707, W0718

from contextlib import asynccontextmanager

from aithena_services.memory.pgvector import (
    close_pool,
    init_pool,
    works_by_similarity_search,
)
from fastapi import FastAPI, HTTPException
from polus.aithena.common.logger import get_logger
from polus.aithena.common.utils import time_logger
from pydantic import BaseModel

logger = get_logger("aithena_services.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - initialize and close connection pool."""
    # Startup
    logger.info("Starting up - initializing database connection pool")
    await init_pool()
    
    yield
    
    # Shutdown
    logger.info("Shutting down - closing database connection pool")
    await close_pool()


app = FastAPI(lifespan=lifespan)


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
@app.post("/memory/pgvector/search_works")
async def search_works_pgvector(request: WorksSearchRequest):
    """
    Perform a similarity search on the specified table using a vector.

    Args:
        request (WorksSearchRequest): The search request containing:
            - table_name: The name of the table to search
            - vector: The vector to use for the similarity search
            - n: The number of results to return (default: 10)

    Returns:
        list[dict]: The search results with work metadata and authorships.

    Raises:
        HTTPException: If an error occurs during the similarity search.
    """
    try:
        res = await works_by_similarity_search(request.table_name, request.vector, request.n)
    except Exception as exc:
        logger.error(f"Error in similarity search: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    return res
