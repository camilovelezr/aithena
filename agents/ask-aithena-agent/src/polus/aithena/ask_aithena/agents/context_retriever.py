"""
This agent is used to retrieve the works that are most relevant to the query.
It uses the semantic agent to get the main topic of the query and then uses the vector search tool to get the works that are most relevant to the query.
"""

from polus.aithena.ask_aithena.agents.semantic_extractor import semantic_agent
from polus.aithena.common.logger import get_logger
from polus.aithena.ask_aithena.models import Context
from polus.aithena.ask_aithena.tools.vector_search import (
    get_similar_works_async,
    get_similar_works,
)
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


async def retrieve_context(query: str) -> Context:
    with logfire.span("context_retriever workflow"):
        logger.info(f"Running context retriever with query: {query}")
        logger.info("Running semantic extracter")
        semantics = await semantic_agent.run(f"Q: {query}")
        logger.info("Running vector search")
        works = await get_similar_works_async(semantics.data.sentence)
        logger.info("Creating context")
        context = Context.from_works(works)
        return context
