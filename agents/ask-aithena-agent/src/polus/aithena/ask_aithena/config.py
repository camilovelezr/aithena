"""Configuration for Ask Aithena Agent."""

from polus.aithena.common.logger import get_logger
from pathlib import Path
import os
from dotenv import find_dotenv, load_dotenv

# Load the environment variables from the .env file in the folder hierarchy.
# The values from the .env file will override the system environment variables.
load_dotenv(find_dotenv(), override=True)

logger = get_logger(__name__)

# logging
LOGFIRE_SERVICE_NAME = os.environ.get(
    "LOGFIRE_SERVICE_NAME", default="ask-aithena-agent"
)
LOGFIRE_SERVICE_VERSION = os.environ.get("LOGFIRE_SERVICE_VERSION", default="1.0.0")

LITELLM_URL = os.environ.get("LITELLM_URL", default="http://localhost:4000/v1")
LITELLM_URL = LITELLM_URL.rstrip("/")
if not LITELLM_URL.endswith("/v1"):
    logger.warning("LITELLM_URL does not end with /v1. Adding it.")
    LITELLM_URL += "/v1"
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", default="sk-1212")
PROMPTS_DIR = os.environ.get("PROMPTS_DIR", default="./prompts")
PROMPTS_DIR = Path(PROMPTS_DIR).resolve()

CHAT_MODEL = os.environ.get("CHAT_MODEL", default="llama3.1:8b")
CHAT_MODEL_BEST_OF = os.environ.get("CHAT_MODEL_BEST_OF", default=None)
CHAT_MODEL_ECHO = os.environ.get("CHAT_MODEL_ECHO", default=None)
CHAT_MODEL_FREQUENCY_PENALTY = os.environ.get(
    "CHAT_MODEL_FREQUENCY_PENALTY", default=None
)
CHAT_MODEL_LOGIT_BIAS = os.environ.get("CHAT_MODEL_LOGIT_BIAS", default=None)
CHAT_MODEL_LOGPROBS = os.environ.get("CHAT_MODEL_LOGPROBS", default=None)
CHAT_MODEL_MAX_TOKENS = os.environ.get("CHAT_MODEL_MAX_TOKENS", default=None)
CHAT_MODEL_TOP_P = os.environ.get("CHAT_MODEL_TOP_P", default=None)
CHAT_MODEL_PRESENCE_PENALTY = os.environ.get(
    "CHAT_MODEL_PRESENCE_PENALTY", default=None
)
CHAT_MODEL_N = os.environ.get("CHAT_MODEL_N", default=None)
CHAT_MODEL_SEED = os.environ.get("CHAT_MODEL_SEED", default=None)
CHAT_MODEL_TEMPERATURE = os.environ.get("CHAT_MODEL_TEMPERATURE", default=None)

CHAT_MODEL_PARAMS = {
    "best_of": CHAT_MODEL_BEST_OF,
    "echo": CHAT_MODEL_ECHO,
    "frequency_penalty": CHAT_MODEL_FREQUENCY_PENALTY,
    "logit_bias": CHAT_MODEL_LOGIT_BIAS,
    "logprobs": CHAT_MODEL_LOGPROBS,
    "max_tokens": CHAT_MODEL_MAX_TOKENS,
    "top_p": CHAT_MODEL_TOP_P,
    "presence_penalty": CHAT_MODEL_PRESENCE_PENALTY,
    "n": CHAT_MODEL_N,
    "seed": CHAT_MODEL_SEED,
    "temperature": CHAT_MODEL_TEMPERATURE,
}
CHAT_MODEL_PARAMS = {k: v for k, v in CHAT_MODEL_PARAMS.items() if v is not None}
SEMANTICS_MODEL = os.environ.get("SEMANTICS_MODEL", default="llama3.2")
SEMANTICS_TEMPERATURE = float(os.environ.get("SEMANTICS_TEMPERATURE", default=0.2))
RERANK_MODEL = os.environ.get("RERANK_MODEL", default="azure-gpt-4o")
RERANK_TEMPERATURE = float(os.environ.get("RERANK_TEMPERATURE", default=0.3))
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", default=10))

EMBEDDING_MODEL = os.environ.get("EMBED_MODEL", default="nomic")
EMBEDDING_TABLE = os.environ.get("EMBEDDING_TABLE", "openalex.nomic_embed_text_768")
SIMILARITY_N = int(os.environ.get("SIMILARITY_N", default=10))

USE_RABBITMQ = os.environ.get("USE_RABBITMQ", default=False)

# Consolidate configuration logging into a single structured log entry
config_values = {
    "litellm_url": LITELLM_URL,
    "litellm_api_key": LITELLM_API_KEY,
    "chat_model": CHAT_MODEL,
    "chat_model_params": CHAT_MODEL_PARAMS,
    "embedding_model": EMBEDDING_MODEL,
    "embedding_table": EMBEDDING_TABLE,
    "similarity_n": SIMILARITY_N,
    "rerank_model": RERANK_MODEL,
    "rerank_temperature": RERANK_TEMPERATURE,
    "rerank_top_k": RERANK_TOP_K,
    "semantics_model": SEMANTICS_MODEL,
    "semantics_temperature": SEMANTICS_TEMPERATURE,
    "prompts_dir": PROMPTS_DIR,
    "use_rabbitmq": USE_RABBITMQ,
}
logger.debug("Configuration values: %s", config_values)
