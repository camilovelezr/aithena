"""Reranker Agent Referee Orchestrator"""

from pathlib import Path
import orjson

from atomic_agents.agents.base_agent import BaseAgent, BaseIOSchema, BaseAgentConfig

import instructor
from polus.aithena.ask_aithena.config import (
    PROMPTS_DIR,
    LITELLM_URL,
    LITELLM_API_KEY,
    RERANK_MODEL,
    RERANK_TEMPERATURE,
    RERANK_TOP_K,
)

from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
from dataclasses import dataclass
import openai
from polus.aithena.common.logger import get_logger
from pydantic_ai import Agent, RunContext
from pydantic import Field, BaseModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from polus.aithena.common.logger import get_logger
from polus.aithena.ask_aithena.models import Context
from polus.aithena.ask_aithena.agents.reranker.aegis.tools import (
    robust_noun_phrase_overlap as robust_tool,
    simplified_ngram_overlap as simplified_tool,
)
from polus.aithena.ask_aithena.agents.reranker.aegis.single_agent import (
    referee_agent,
    RefereeDeps,
)
import logfire

logfire.configure()
logfire.instrument_openai()

logger = get_logger(__name__)

PROMPT = Path(PROMPTS_DIR, "reranker", "referee", "orchestrator.txt").read_text()


class AegisRerankedWork(BaseModel):
    """A reranked work."""

    index: int = Field(..., description="The index of the work")
    score: float = Field(..., description="The relevance score of the work")
    reason: str = Field(..., description="The reason for the score")


class AegisRerankerDeps(BaseModel):
    """Dependencies for the Reranker Agent."""

    query: str = Field(..., description="The original user query")
    works: Context = Field(..., description="The list of works to rerank")


# class RerankerOutput(BaseModel):
#     """Output for the Reranker Agent."""

#     reranked_works: list[RerankedWork] = Field(
#         ..., description="The reranked list of works"
#     )


model = OpenAIModel(
    "azure-gpt-4o",
    provider=OpenAIProvider(base_url=LITELLM_URL, api_key=LITELLM_API_KEY),
)

aegis_reranker_agent = Agent(
    model=model,
    system_prompt=PROMPT,
    deps_type=AegisRerankerDeps,
    # result_type=RerankerOutput,
    result_type=list[AegisRerankedWork],
)


@aegis_reranker_agent.system_prompt
async def system_prompt(ctx: RunContext[AegisRerankerDeps]) -> str:
    """System prompt for the Reranker Agent."""

    indx = [_ for _ in range(len(ctx.deps.works.documents))]
    return f"<query>{ctx.deps.query}</query>\n<indices>{indx}</indices>"


@aegis_reranker_agent.tool
async def score_work(
    ctx: RunContext[AegisRerankerDeps], index: int, effective_prompt: str
) -> AegisRerankedWork:
    """Score a work.
    Args:
        index: the index of the work to score
        effective_prompt: the effective prompt to pass to the referee agent
    Returns:
        the relevance score of the work
    """

    deps = RefereeDeps(
        query=ctx.deps.query, work=ctx.deps.works.works_for_reranker[index]
    )
    res = await referee_agent.run(effective_prompt, deps=deps)
    return AegisRerankedWork(index=index, score=res.data.score, reason=res.data.reason)


async def aegis_rerank_context(query: str, context: Context) -> Context:
    """Rerank the context based on the query."""
    with logfire.span("aegis_rerank_context"):
        logger.info(f"Aegis Reranking context for query: {query}")
        logger.info(f"Context: {context.model_dump_json()}")
        reranked_data = await aegis_reranker_agent.run(
            "You are an expert reranker who's super careful",
            deps=AegisRerankerDeps(query=query, works=context),
        )
        logger.info(f"Reranked data: {reranked_data.data}")
        reranker_inds = [x.index for x in reranked_data.data]
        reranker_scores = [x.score for x in reranked_data.data]
        reranker_reasons = [x.reason for x in reranked_data.data]
        context.reranked_indices = reranker_inds
        context.reranked_scores = reranker_scores
        context.reranked_reasons = reranker_reasons
        return context


# query_test = "What is the effect of national diversity on a team's success?"

# from polus.aithena.ask_aithena.agents import big_agent

# context = big_agent.run(query_test)

# import nest_asyncio

# nest_asyncio.apply()

# deps = RerankerDeps(query=query_test, works=context)
# res = reranker_agent.run_sync(
#     "Rerank the works based on the scores returned by the score_work tool.",
#     deps=deps,
# )


# from pprint import pprint
# pprint(res.data.model_dump())
