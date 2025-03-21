"""
This module contains the logic for the narrator agent.
It is an agent that will narrate the conversation to the user.
"""

import asyncio
from pathlib import Path

from pydantic import Field, BaseModel
from polus.aithena.ask_aithena.config import (
    LITELLM_URL,
    LITELLM_API_KEY,
    PROMPTS_DIR,
)
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from polus.aithena.common.logger import get_logger

# import logfire

# logfire.configure()
# logfire.instrument_openai()

logger = get_logger(__name__)

# PROMPTS_DIR = Path("/Users/cv/code/aithena/agents/ask-aithena-agent/prompts")
PROMPT = Path(PROMPTS_DIR, "narrator.txt").read_text()

model = OpenAIModel(
    model_name="gemma3-1b",
    provider=OpenAIProvider(
        api_key=LITELLM_API_KEY,
        base_url=LITELLM_URL,
    ),
)


narrator_agent = Agent(
    model=model,
    system_prompt=PROMPT,
    result_type=str,
    model_settings=ModelSettings(temperature=0.9),
)

import nest_asyncio

nest_asyncio.apply()
from pprint import pprint

nar = (
    "Okay, I see you’re asking about advancements in nuclear medicine utilizing "
    "artificial intelligence. Let me begin my search for relevant documents."
)
pprint(
    narrator_agent.run_sync(
        f"<instructions>Communicate that we retrieved 10 documents and now we will analyze them to check if they are relevant to the user's query.</instructions><narration>{nar}</narration> "
    ).data
)
