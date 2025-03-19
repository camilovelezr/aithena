"""Configuration settings for the OpenAlex package.

This module centralizes all environment variable loading for consistent access
throughout the package.
"""

import os

from dotenv import find_dotenv, load_dotenv
from polus.aithena.common.logger import get_logger

logger = get_logger(__name__)

# Load environment variables from .env file if present
env_file = find_dotenv()
if env_file:
    logger.info(f"Loading environment from {env_file}")
    load_dotenv(env_file, override=True)
else:
    logger.warning("No .env file found, using environment variables only")


# =============================================
# S3 Operation Variables
# =============================================

# Determine if we should download from the last month automatically
S3_ALL_LAST_MONTH = os.getenv("ALL_LAST_MONTH", "False")
S3_ALL_LAST_MONTH = S3_ALL_LAST_MONTH in ["True", "true", "1"]

# Output directory for S3 downloads
S3_OUTPUT_PATH = os.getenv("S3_OUT_DIR", None)

# Starting date for S3 downloads
S3_FROM_DATE = os.getenv("S3_FROM_DATE", None)

# =============================================
# REST API Variables
# =============================================

# API host and port
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PYALEX_EMAIL = os.getenv("PYALEX_EMAIL", None)

# =============================================
# PostgreSQL connection
# =============================================
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
DB_CONFIG_STRING = f"dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD} host={POSTGRES_HOST} port={POSTGRES_PORT}"

# Print the constructed DB_CONFIG_STRING for debugging
print(f"DEBUG CONFIG: DB_CONFIG_STRING={DB_CONFIG_STRING}")

# Job database URL for tracking update jobs
JOB_DATABASE_URL = os.getenv("JOB_DATABASE_URL", "sqlite:///./openalex_jobs.db")

# =============================================
# Update Job Configuration
# =============================================

# Number of records to process in a batch
UPDATE_BATCH_SIZE = int(os.getenv("UPDATE_BATCH_SIZE", "100"))

# Maximum number of records to process in a single job
UPDATE_MAX_RECORDS = int(os.getenv("UPDATE_MAX_RECORDS", "10000"))

# =============================================
# API Request Configuration
# =============================================

# OpenAlex API key (if available)
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", None)

# Default timeout for API requests in seconds
API_REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", "30"))

# Maximum retries for API requests
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))

logger.debug(
    f"""
             Initiliazed get-openalex config with: 
             S3_ALL_LAST_MONTH={S3_ALL_LAST_MONTH}, 
             S3_OUTPUT_PATH={S3_OUTPUT_PATH}, 
             S3_FROM_DATE={S3_FROM_DATE}, 
             UPDATE_BATCH_SIZE={UPDATE_BATCH_SIZE}, 
             UPDATE_MAX_RECORDS={UPDATE_MAX_RECORDS}, 
             API_HOST={API_HOST}, 
             API_PORT={API_PORT}, 
             LOG_LEVEL={LOG_LEVEL}, 
             PYALEX_EMAIL={PYALEX_EMAIL}, 
             DB_CONFIG_STRING={DB_CONFIG_STRING}, 
             JOB_DATABASE_URL={JOB_DATABASE_URL}, 
             API_REQUEST_TIMEOUT={API_REQUEST_TIMEOUT}, 
             API_MAX_RETRIES={API_MAX_RETRIES}, OPENALEX_API_KEY={OPENALEX_API_KEY}"""
)
