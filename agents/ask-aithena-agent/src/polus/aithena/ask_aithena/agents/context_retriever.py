"""
This agent is used to retrieve the works that are most relevant to the query.
It uses the semantic agent to get the main topic of the query and then uses the vector search tool to get the works that are most relevant to the query.
"""

from polus.aithena.ask_aithena.agents.semantic_extractor import run_semantic_agent
from polus.aithena.ask_aithena.rabbit import (
    ask_aithena_exchange,
    ask_aithena_queue,
    ProcessingStatus,
)
from polus.aithena.common.logger import get_logger
from polus.aithena.ask_aithena.models import Context
from polus.aithena.ask_aithena.tools.vector_search import (
    get_similar_works_async,
)
from faststream.rabbit.broker import RabbitBroker
from typing import Optional
from polus.aithena.ask_aithena.logfire_logger import logfire
from polus.aithena.ask_aithena.config import USE_LOGFIRE

if USE_LOGFIRE:
    logfire.instrument_openai()

logger = get_logger(__name__)


async def retrieve_context(
    query: str,
    similarity_n: int,
    broker: Optional[RabbitBroker] = None,
    session_id: Optional[str] = None,
) -> Context:
    if USE_LOGFIRE:
        with logfire.span("context_retriever workflow"):
            logger.info(f"Running context retriever with query: {query}")
            logger.info("Running semantic extractor")
            semantics = await run_semantic_agent(query, broker, session_id)
            await broker.publish(
                ProcessingStatus(
                    status="searching_for_works",
                    message=f"Now I will search for works related to {semantics.output.sentence.lower()}...",
                ).model_dump_json(),
                exchange=ask_aithena_exchange,
                queue=ask_aithena_queue,
                routing_key=session_id,
            )
            logger.info("Running vector search")
            works = await get_similar_works_async(
                semantics.output.sentence, similarity_n, broker, session_id
            )
            logger.info("Creating context")
            context = Context.from_works(works)
            return context
    else:
        logger.info(f"Running context retriever with query: {query}")
        logger.info("Running semantic extractor")
        semantics = await run_semantic_agent(query, broker, session_id)
        await broker.publish(
            ProcessingStatus(
                status="searching_for_works",
                message=f"Now I will search for works related to {semantics.output.sentence.lower()}...",
            ).model_dump_json(),
            exchange=ask_aithena_exchange,
            queue=ask_aithena_queue,
            routing_key=session_id,
        )
        logger.info("Running vector search")
        works = await get_similar_works_async(
            semantics.output.sentence, similarity_n, broker, session_id
        )
        logger.info("Creating context")
        context = Context.from_works(works)
        return context