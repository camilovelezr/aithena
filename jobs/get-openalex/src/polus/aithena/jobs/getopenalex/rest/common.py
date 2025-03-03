"""Common utilities for the OpenAlex REST API."""

# Local imports
from polus.aithena.common.logger import get_logger
from polus.aithena.jobs.getopenalex.config import API_REQUEST_TIMEOUT, API_MAX_RETRIES

logger = get_logger(__name__)


class OpenAlexError(Exception):
    """Base exception for OpenAlex API errors"""

    pass


class RateLimitError(OpenAlexError):
    """Exception raised when hitting rate limits"""

    pass


class APIError(OpenAlexError):
    """Exception raised for API errors"""

    pass


# Constants
DEFAULT_TIMEOUT = API_REQUEST_TIMEOUT  # seconds
MAX_RETRIES = API_MAX_RETRIES
RATE_LIMIT_DELAY = 1  # second
logger.debug(f"DEFAULT_TIMEOUT: {DEFAULT_TIMEOUT}")
logger.debug(f"MAX_RETRIES: {MAX_RETRIES}")
logger.debug(f"RATE_LIMIT_DELAY: {RATE_LIMIT_DELAY}")
