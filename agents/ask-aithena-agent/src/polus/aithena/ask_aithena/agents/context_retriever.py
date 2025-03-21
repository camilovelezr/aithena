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
    get_similar_works,
)
from faststream.rabbit.broker import RabbitBroker
from typing import Optional
import logfire

logfire.configure()
logfire.instrument_openai()

logger = get_logger(__name__)


# import nest_asyncio

# nest_asyncio.apply()


def retrieve_context_sync(query: str) -> Context:
    with logfire.span("context_retriever workflow"):
        logger.info(f"Running context retriever with query: {query}")
        logger.info("Running semantic extracter")
        semantics = semantic_agent.run_sync(f"Q: {query}")
        logger.info("Running vector search")
        works = get_similar_works(semantics.data.sentence)
        logger.info("Creating context")
        context = Context.from_works(works)
        return context


async def retrieve_context(
    query: str, similarity_n: int, broker: Optional[RabbitBroker] = None
) -> Context:
    with logfire.span("context_retriever workflow"):
        logger.info(f"Running context retriever with query: {query}")
        logger.info("Running semantic extracter")
        semantics = await run_semantic_agent(query, broker)
        await broker.publish(
            ProcessingStatus(
                status="searching_for_works",
                message=f"Now I will search for works related to {semantics.data.sentence.lower()}...",
            ).model_dump_json(),
            exchange=ask_aithena_exchange,
            queue=ask_aithena_queue,
        )
        logger.info("Running vector search")
        works = await get_similar_works_async(
            semantics.data.sentence, similarity_n, broker
        )
        logger.info("Creating context")
        context = Context.from_works(works)
        return context
