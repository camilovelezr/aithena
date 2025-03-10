import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from polus.aithena.common.logger import get_logger

logger = get_logger(__file__)

load_dotenv(find_dotenv(), override=True)
logger.info(f"Loaded environment variables from {find_dotenv()}")


# ----Memory----
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")


logger.info(
    f"""
Aithena-Services started with 
POSTGRES_HOST: {POSTGRES_HOST}, POSTGRES_PORT: {POSTGRES_PORT}, POSTGRES_USER: {POSTGRES_USER}, POSTGRES_PASSWORD: {"*" * len(POSTGRES_PASSWORD)},
POSTGRES_DB: {POSTGRES_DB}
"""
)


__all__ = [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
]
