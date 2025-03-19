"""
This module contains the logic for the semantic agent.
It is a self-supervised agent that will extract a sentence from a user query.
"""

from pathlib import Path
from typing import Optional

import orjson
from atomic_agents.agents.base_agent import BaseAgent, BaseIOSchema, BaseAgentConfig
from pydantic import Field, BaseModel
import instructor
from polus.aithena.ask_aithena.config import (
    LITELLM_URL,
    LITELLM_API_KEY,
    SEMANTICS_MODEL,
    SEMANTICS_TEMPERATURE,
    PROMPTS_DIR,
)
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
import openai
from polus.aithena.common.logger import get_logger
import logfire
import datetime
from faststream.rabbit import RabbitBroker

from polus.aithena.ask_aithena.rabbit import ProcessingStatus


logfire.configure()
logfire.instrument_openai()

logger = get_logger(__name__)

PROMPTS_DIR = PROMPTS_DIR.joinpath("semantics")
EXTRACT_SEMANTICS_AGENT_PROMPT = orjson.loads(
    Path(PROMPTS_DIR, "extract_agent.json").read_text()
)
MAIN_AGENT_PROMPT = Path(PROMPTS_DIR, "main_agent.txt").read_text()


class ExtractSemanticAgentInput(BaseIOSchema):
    """User's original query, we want to extract the main topic from this query."""

    query: str = Field(..., description="The original user query")
    extra_instructions: Optional[str] = Field(
        None,
        description="Optional important considerations that you should take into account when extracting the main topic from the user's query.",
    )


class ExtractSemanticAgentOutput(BaseIOSchema):
    """Sentence that captures the main idea of the question in an appropriate syntax for vector embedding."""

    sentence: str = Field(
        ...,
        description="The sentence that captures the main idea of the question in an appropriate syntax for vector embedding.",
    )


class SemanticAgentOutput(BaseModel):
    """Sentence that captures the main idea of the question in an appropriate syntax for vector embedding."""

    sentence: str = Field(
        ...,
        description="The sentence that captures the main idea of the question in an appropriate syntax for vector embedding.",
    )


extract_semantic_agent = BaseAgent(
    BaseAgentConfig(
        client=instructor.from_openai(
            openai.OpenAI(base_url=LITELLM_URL, api_key=LITELLM_API_KEY)
        ),
        model=SEMANTICS_MODEL,
        temperature=SEMANTICS_TEMPERATURE,
        system_prompt_generator=SystemPromptGenerator(
            background=EXTRACT_SEMANTICS_AGENT_PROMPT["background"],
            steps=EXTRACT_SEMANTICS_AGENT_PROMPT["steps"],
            output_instructions=EXTRACT_SEMANTICS_AGENT_PROMPT["output_instructions"],
        ),
        input_schema=ExtractSemanticAgentInput,
        output_schema=ExtractSemanticAgentOutput,
    )
)

model = OpenAIModel(
    model_name="azure-gpt-4o",
    provider=OpenAIProvider(
        base_url=LITELLM_URL,
        api_key=LITELLM_API_KEY,
    ),
)

semantic_agent = Agent(
    model=model,
    system_prompt=MAIN_AGENT_PROMPT,
    result_type=SemanticAgentOutput,
    instrument=True,
)


@semantic_agent.tool_plain
async def extract_semantics(
    query: str, extra_instructions: Optional[str] = None
) -> str:
    """Extract the main idea of the question in an appropriate syntax for vector embedding.
    This calls an 'expert' LLM that will extract a potential sentence S from user query Q.

    Args:
        query: The original user query
        extra_instructions: optional important considerations passed to the expert LLM.
    """

    inp = ExtractSemanticAgentInput(query=query, extra_instructions=extra_instructions)
    res = extract_semantic_agent.run(inp)
    return res.sentence


async def run_semantic_agent(
    query: str, broker: Optional[RabbitBroker] = None, session_id: Optional[str] = None
) -> SemanticAgentOutput:
    """Run the semantic agent on a query.

    Args:
        query: The original user query
        broker: The broker to use to publish status messages
        session_id: The session ID to use for the status messages
    """
    if broker is not None:
        await broker.publish(
            ProcessingStatus(
                query_id=session_id,
                stage="analyzing_query",
            ).model_dump_json(),
        )

    res = await semantic_agent.run(f"Q: {query}")

    return res.data


# query_test = "What is the effect of national diversity on a team's success?"
# query_test = "I am a molecular biologist interested in phylogenetic studies, are there any papers relating phylogenetics to cancer research?"
# query_test = (
#     "What is the effect of changing the temperature of an LLM on real time results?"
# )


# async def main():
#     # Run setup first

#     # Start the broker
#     # First, test direct publication to see if it works

#     # Then test extract_semantics to see if it works
#     broker = RabbitBroker("amqp://guest:guest@localhost:5672/")
#     await broker.start()
#     await broker.publish(
#         ProcessingStatus(
#             query_id="123",
#             timestamp=datetime.datetime.now().isoformat(),
#             stage="analyzing_query",
#             details={"query": query_test},
#         ).model_dump_json(),
#         queue="semantic-agent-status",
#     )
#     await extract_semantics(query_test)
#     await broker.publish(
#         ProcessingStatus(
#             query_id="123",
#             timestamp=datetime.datetime.now().isoformat(),
#             stage="query_analysis_completed",
#         ).model_dump_json(),
#         queue="semantic-agent-status",
#     )

#     # Finally try the semantic agent
#     await broker.publish(
#         ProcessingStatus(
#             query_id="123",
#             timestamp=datetime.datetime.now().isoformat(),
#             stage="extracting_semantics",
#         ).model_dump_json(),
#         queue="semantic-agent-status",
#     )
#     res = await semantic_agent.run(f"Q: {query_test}")
#     await broker.publish(
#         ProcessingStatus(
#             query_id="123",
#             timestamp=datetime.datetime.now().isoformat(),
#             stage="semantic_agent_completed",
#         ).model_dump_json(),
#         queue="semantic-agent-status",
#     )
#     from pprint import pprint

#     pprint(res)
#     await broker.close()


# if __name__ == "__main__":
#     asyncio.run(main())
