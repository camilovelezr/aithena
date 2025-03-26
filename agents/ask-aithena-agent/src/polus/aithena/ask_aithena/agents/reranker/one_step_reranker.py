from pathlib import Path
import orjson

from atomic_agents.agents.base_agent import BaseAgent, BaseIOSchema, BaseAgentConfig

import instructor
from polus.aithena.ask_aithena.config import (
    PROMPTS_DIR,
    LITELLM_URL,
    LITELLM_API_KEY,
)

from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
import openai
from polus.aithena.common.logger import get_logger
from pydantic_ai import Agent, RunContext
from pydantic import Field, BaseModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from polus.aithena.common.logger import get_logger
from polus.aithena.ask_aithena.models import Context
from polus.aithena.ask_aithena.config import USE_LOGFIRE
from polus.aithena.ask_aithena.logfire_logger import logfire

if USE_LOGFIRE:
    logfire.configure()
    logfire.instrument_openai()

logger = get_logger(__name__)

PROMPTS_DIR = PROMPTS_DIR.joinpath("reranker")
RERANKER_AGENT_PROMPT = Path(PROMPTS_DIR, "one_step_agent.txt").read_text()
RERANKER_CREATE_PROMPT = orjson.loads(
    Path(PROMPTS_DIR, "create_prompt.json").read_text()
)
RERANKER_DESCRIBE_WORKS_PROMPT = orjson.loads(
    Path(PROMPTS_DIR, "describe_works.json").read_text()
)
RERANKER_DEFINE_TOPIC_PROMPT = orjson.loads(
    Path(PROMPTS_DIR, "define_topic.json").read_text()
)


class RerankerDeps(BaseModel):
    """Query and context for the reranker.

    Args:
        query: The original user query
        context: The Context object
    """

    query: str = Field(..., description="The original user query")
    context: Context = Field(
        ...,
        description="The context that will be used to eventually generate the chat response from RAG",
    )


class RerankedWork(BaseModel):
    """A reranked work with its index and score."""

    index: int = Field(..., description="The index of the work")
    score: float = Field(..., description="The score of the work")


model = OpenAIModel(
    "azure-gpt-4o",
    provider=OpenAIProvider(base_url=LITELLM_URL, api_key=LITELLM_API_KEY),
)
reranker_agent = Agent(
    model=model,
    system_prompt=RERANKER_AGENT_PROMPT,
    deps_type=RerankerDeps,
    instrument=USE_LOGFIRE,
    result_type=list[RerankedWork],
)


@reranker_agent.system_prompt
async def prepare_prompt(ctx: RunContext[RerankerDeps]) -> str:
    return f"""
    <query>{ctx.deps.query}</query>
    <works>{ctx.deps.context.to_works_for_reranker()}</works>
    """


@reranker_agent.tool
async def verify_result_list(ctx: RunContext[RerankerDeps], result: list) -> bool:
    """
    Verify the length of the result indices list and the uniqueness of the indices.
    This tool also verifies that the order of the indices is correct.
    ALWAYS run this tool after using call_reranker tool to verify
    the result of the reranking.

    If the length of the result indices list is not equal to the number of works in the original list of works,
    you will need to call call_reranker tool again, adding "make sure your result contains X UNIQUE indices in [0,1] and
    that the order of the results is from most relevant to least relevant" to the argument
    'prompt', where X is the number of works in the original list of works.
    """
    if len(result) != len(ctx.deps.context.documents):
        return False
    if len(result) != len(set([x["index"] for x in result])):
        return False
    scores = [x["score"] for x in result]
    if any(score < 0 or score > 1 for score in scores):
        return False
    if sorted(scores, reverse=True) != scores:
        return False
    return True


class DefineTopicInput(BaseIOSchema):
    """User's original query, we want to extract the main topic from this query."""

    query: str = Field(..., description="The original user query")


class DefineTopicOutput(BaseIOSchema):
    """The main broad topic of the user's original query that we extracted."""

    broad_topic: str = Field(..., description="The main broad topic of the query")


define_topic_agent = BaseAgent(
    BaseAgentConfig(
        client=instructor.from_openai(
            openai.OpenAI(base_url=LITELLM_URL, api_key=LITELLM_API_KEY)
        ),
        model="llama3.2",
        temperature=0.3,
        system_prompt_generator=SystemPromptGenerator(
            background=RERANKER_DEFINE_TOPIC_PROMPT["background"],
            steps=RERANKER_DEFINE_TOPIC_PROMPT["steps"],
            output_instructions=RERANKER_DEFINE_TOPIC_PROMPT["output_instructions"],
        ),
        input_schema=DefineTopicInput,
        output_schema=DefineTopicOutput,
    )
)


@reranker_agent.tool
async def define_broad_topic(ctx: RunContext[RerankerDeps]) -> str:
    """
    Define the main broad topic of the query.
    For example, if query is "What is the best treatment for depression?",
    the broad topic could be "clinical depression" or "mental health" or "medicine".
    """
    res = define_topic_agent.run(DefineTopicInput(query=ctx.deps.query))
    return res.broad_topic


class DescribeWorksInput(BaseIOSchema):
    """The original list of works, we want to describe each work in a concise manner."""

    works: str = Field(..., description="The original list of works")
    query: str = Field(..., description="The original user query")


class DescribeWorksOutput(BaseIOSchema):
    """The description of the works in a concise manner."""

    description: str = Field(
        ...,
        description="The description of the works in the appropriate format",
    )


describe_works_agent = BaseAgent(
    BaseAgentConfig(
        client=instructor.from_openai(
            openai.OpenAI(base_url=LITELLM_URL, api_key=LITELLM_API_KEY)
        ),
        model="azure-gpt-4o-mini",
        system_prompt_generator=SystemPromptGenerator(
            background=RERANKER_DESCRIBE_WORKS_PROMPT["background"],
            steps=RERANKER_DESCRIBE_WORKS_PROMPT["steps"],
            output_instructions=RERANKER_DESCRIBE_WORKS_PROMPT["output_instructions"],
        ),
        input_schema=DescribeWorksInput,
        output_schema=DescribeWorksOutput,
        model_api_parameters={"temperature": 0.3},
    )
)


@reranker_agent.tool
async def describe_works(ctx: RunContext[RerankerDeps]) -> str:
    """
    Describe the works in a concise manner.
    """
    res = describe_works_agent.run(
        DescribeWorksInput(
            works=f"<works>{ctx.deps.context.to_works_for_reranker()}</works>",
            query=f"<query>{ctx.deps.query}</query>",
        )
    )
    return res.description


class CreateRerankerPromptInput(BaseIOSchema):
    """Input for the reranker prompt agent that contains the original list of works, the main broad topic of the query, and the description of the works."""

    works: str = Field(..., description="The original list of works as a single string")
    broad_topic: str = Field(
        ..., description="The main broad topic of the user's query"
    )
    description: str = Field(
        ..., description="The description of the works as a single string"
    )


class CreateRerankerPromptOutput(BaseIOSchema):
    """The generated prompt for the reranker."""

    prompt: str = Field(..., description="The generated prompt for the reranker")


create_reranker_prompt_agent = BaseAgent(
    BaseAgentConfig(
        client=instructor.from_openai(
            openai.OpenAI(base_url=LITELLM_URL, api_key=LITELLM_API_KEY)
        ),
        model="azure-gpt-4o",
        system_prompt_generator=SystemPromptGenerator(
            background=RERANKER_CREATE_PROMPT["background"],
            steps=RERANKER_CREATE_PROMPT["steps"],
            output_instructions=RERANKER_CREATE_PROMPT["output_instructions"],
        ),
        input_schema=CreateRerankerPromptInput,
        output_schema=CreateRerankerPromptOutput,
    )
)


@reranker_agent.tool
async def create_reranker_prompt(
    ctx: RunContext[RerankerDeps],
    broad_topic: str,
    works_description: str,
) -> str:
    """
    Create a prompt for the reranker.

    Args:
        broad_topic: The main broad topic of the query
        works_description: The concise description of the works
    """
    res = create_reranker_prompt_agent.run(
        CreateRerankerPromptInput(
            works=f"<works>{ctx.deps.context.to_works_for_reranker()}</works>",
            broad_topic=broad_topic,
            description=works_description,
        )
    )
    return res.prompt


class CallRerankerInput(BaseIOSchema):
    """Input for the reranker agent that contains the original user query, the original list of works, and the prompt for the reranker."""

    query: str = Field(..., description="The original user query")
    main_topic: str = Field(..., description="The main broad topic of the query")
    works: str = Field(..., description="The original list of works")
    works_description: str = Field(
        ..., description="The concise description of the works"
    )
    instructions: str = Field(..., description="The instructions for the reranker")


class CallRerankerOutput(BaseIOSchema):
    """The reranked list of works' indices."""

    reranked_works: list[RerankedWork] = Field(
        ..., description="The reranked list of works' indices and their scores"
    )


call_reranker_agent = BaseAgent(
    BaseAgentConfig(
        client=instructor.from_openai(
            openai.OpenAI(base_url=LITELLM_URL, api_key=LITELLM_API_KEY)
        ),
        model="azure-gpt-4o",
        system_prompt_generator=SystemPromptGenerator(
            background=[
                "You are an expert in reranking works based on a user's query."
            ],
            steps=[
                "Read the instructions and carefully implement all steps necessary."
            ],
            output_instructions=[
                "Make sure you follow the output format specified in instructions."
            ],
        ),
        input_schema=CallRerankerInput,
        output_schema=CallRerankerOutput,
    )
)


@reranker_agent.tool
async def call_reranker(
    ctx: RunContext[RerankerDeps],
    main_topic: str,
    works_description: str,
    prompt: str,
) -> list:
    """
    Call the reranker with the prompt generated by create_reranker_prompt tool
    You will need to pass the original list of works, the main broad topic of the query, and the description of the works to the reranker.

    Args:
        main_topic: The main broad topic of the query generated by define_broad_topic tool
        works_description: The concise description of the works generated by describe_works tool
        prompt: The prompt for the reranker, generated by create_reranker_prompt tool
    """
    res = call_reranker_agent.run(
        CallRerankerInput(
            query=ctx.deps.query,
            main_topic=main_topic,
            works=ctx.deps.context.to_works_for_reranker(),
            works_description=works_description,
            instructions=prompt,
        )
    )
    return res.reranked_works


async def rerank_context(query: str, context: Context) -> Context:
    """Rerank the context based on the query."""
    if USE_LOGFIRE:
        with logfire.span("one_step_reranker"):
            logger.info(f"One Step Reranking context for query: {query}")
            logger.info(f"Context: {context.model_dump_json()}")
            reranked_data = await reranker_agent.run(
                "You are an expert reranker who's super careful",
                deps=RerankerDeps(query=query, context=context),
            )
            logger.info(f"Reranked data: {reranked_data.data}")
            reranker_inds = [x.index for x in reranked_data.data]
            reranker_scores = [x.score for x in reranked_data.data]
            context.reranked_indices = reranker_inds
            context.reranked_scores = reranker_scores
            return context
    else:
        logger.info(f"One Step Reranking context for query: {query}")
        logger.info(f"Context: {context.model_dump_json()}")
        reranked_data = await reranker_agent.run(
            "You are an expert reranker who's super careful",
            deps=RerankerDeps(query=query, context=context),
        )
        logger.info(f"Reranked data: {reranked_data.data}")
        reranker_inds = [x.index for x in reranked_data.data]
        reranker_scores = [x.score for x in reranked_data.data]
        context.reranked_indices = reranker_inds
        context.reranked_scores = reranker_scores
        return context
