"""
This module contains the logic for the talker agent.
It is an agent that will talk to a user after the responder agent has answered the initial question.
"""

from pathlib import Path

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
from polus.aithena.ask_aithena.config import TALKER_MODEL, TALKER_MODEL_PARAMS
from polus.aithena.ask_aithena.config import USE_LOGFIRE
from polus.aithena.ask_aithena.logfire_logger import logfire

if USE_LOGFIRE:
    logfire.instrument_openai()

logger = get_logger(__name__)

PROMPT = Path(PROMPTS_DIR, "talker.txt").read_text()

model = OpenAIModel(
    model_name=TALKER_MODEL,
    provider=OpenAIProvider(
        api_key=LITELLM_API_KEY,
        base_url=LITELLM_URL,
    ),
)


talker_agent = Agent(
    model=model,
    system_prompt=PROMPT,
    output_type=str,
    instrument=USE_LOGFIRE,
    model_settings=ModelSettings(**TALKER_MODEL_PARAMS),
)
