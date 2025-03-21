import httpx
from openai import OpenAI

from polus.aithena.ask_aithena.config import (
    LITELLM_URL,
    LITELLM_API_KEY,
    EMBEDDING_MODEL,
    SIMILARITY_N,
    EMBEDDING_TABLE,
)
from polus.aithena.common.logger import get_logger
from faststream.rabbit import RabbitBroker
from polus.aithena.ask_aithena.rabbit import (
    ask_aithena_exchange,
    ask_aithena_queue,
    ProcessingStatus,
)
import logfire
from typing import Optional

logfire.configure()

logger = get_logger(__name__)

client = OpenAI(base_url=LITELLM_URL, api_key=LITELLM_API_KEY)


def _embed_text(text: str) -> list[float]:
    """Embed text using OpenAI's embedding API.
    Not meant to be used directly. Use get_similar_works or get_similar_works_async instead.
    """
    logger.info(f"Embedding text: {text}")
    logfire.info(f"Embedding text: {text}")
    try:
        return (
            client.embeddings.create(input=text, model=EMBEDDING_MODEL)
            .data[0]
            .embedding
        )
    except Exception as e:
        logger.error(f"Error embedding text: {e}")
        logfire.error(f"Error embedding text: {e}")
        raise e


def get_similar_works(text: str) -> list[dict]:
    """Get similar works from the database."""
    emb = _embed_text(text)
    try:
        with httpx.Client() as client:
            logfire.instrument_httpx(client, capture_headers=True)
            response = client.post(
                f"{LITELLM_URL.rstrip('v1/')}/memory/pgvector/search_works",
                json={"vector": emb, "n": SIMILARITY_N, "table_name": EMBEDDING_TABLE},
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error getting similar works synchronously: {e}")
        logfire.error(f"Error getting similar works synchronously: {e}")
        raise e


async def get_similar_works_async(
    text: str, similarity_n: int, broker: Optional[RabbitBroker] = None
) -> list[dict]:
    """Asynchronously get similar works from the database."""
    emb = _embed_text(text)
    if broker is not None:
        await broker.publish(
            ProcessingStatus(
                status="finding_relevant_documents",
                message=f"Searching through my database...",
            ).model_dump_json(),
            exchange=ask_aithena_exchange,
            queue=ask_aithena_queue,
            routing_key="session.123",
        )
    try:
        async with httpx.AsyncClient() as client:
            logfire.instrument_httpx(client, capture_headers=True)
            response = await client.post(
                f"{LITELLM_URL.rstrip('v1/')}/memory/pgvector/search_works",
                json={"vector": emb, "n": similarity_n, "table_name": EMBEDDING_TABLE},
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error getting similar works asynchronously: {e}")
        logfire.error(f"Error getting similar works asynchronously: {e}")
        raise e
