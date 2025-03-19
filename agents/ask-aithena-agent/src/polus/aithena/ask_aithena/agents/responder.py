"""
This module contains the logic for the responder agent.
It is an agent that will respond to a user query.
"""

import asyncio
from pathlib import Path

from pydantic import Field, BaseModel
import instructor
from polus.aithena.ask_aithena.config import (
    LITELLM_URL,
    LITELLM_API_KEY,
    SEMANTICS_MODEL,
    SEMANTICS_TEMPERATURE,
    PROMPTS_DIR,
)
from polus.aithena.ask_aithena.models import Context
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent
from polus.aithena.common.logger import get_logger
import logfire

logfire.configure()
logfire.instrument_openai()

logger = get_logger(__name__)

# PROMPTS_DIR = Path("/Users/cv/code/aithena/agents/ask-aithena-agent/prompts")
PROMPT = Path(PROMPTS_DIR, "responder.txt").read_text()

model = OpenAIModel(
    model_name="azure-gpt-4.5",
    provider=OpenAIProvider(
        api_key=LITELLM_API_KEY,
        base_url=LITELLM_URL,
    ),
)


responder_agent = Agent(
    model=model, system_prompt=PROMPT, result_type=str, instrument=True
)

# import nest_asyncio

# nest_asyncio.apply()

# from polus.aithena.ask_aithena.agents.context_retriever import retrieve_context
# from polus.aithena.ask_aithena.agents.reranker.one_step_reranker import (
#     reranker_agent,
#     RerankerDeps,
# )

# query = "What are some uses of AI in the field of medicine?"
# RetrievedContext = retrieve_context(query)
# reranker_result = reranker_agent.run_sync(
#     "Be careful with the ordering of tool calls!",
#     deps=RerankerDeps(query=query, context=RetrievedContext),
# )
# reranker_inds = [x.index for x in reranker_result.data]
# reranker_scores = [x.score for x in reranker_result.data]
# RetrievedContext.reranked_indices = reranker_inds
# RetrievedContext.reranked_scores = reranker_scores

# from pprint import pprint


# # Define an async function to handle streaming responses
# async def run_responder(query: str, context: Context):
#     async with responder_agent.run_stream(
#         f"""
#         <question>{query}</question>
#         <context>{context.to_llm_context()}</context>
#         """
#     ) as response:
#         async for message in response.stream_text(delta=True):
#             yield message


# # Use nest_asyncio to run the async function in the current event loop
# # Since we've already applied nest_asyncio above, we can use it directly
# asyncio.run(run_responder(query, RetrievedContext))

# pprint(RetrievedContext.to_references())


# print(RetrievedContext.to_references())
# from pprint import pprint
# pprint(RetrievedContext.to_references())
# pprint(RetrievedContext.to_llm_context())
# RetrievedContext.documents[1]
# print(reranker_result.data)
