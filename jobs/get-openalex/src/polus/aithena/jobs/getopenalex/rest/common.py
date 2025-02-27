"""Common utilities for the OpenAlex REST API."""

# Local imports
from polus.aithena.common.logger import get_logger

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
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1  # second
logger.debug(f"DEFAULT_TIMEOUT: {DEFAULT_TIMEOUT}")
logger.debug(f"MAX_RETRIES: {MAX_RETRIES}")
logger.debug(f"RATE_LIMIT_DELAY: {RATE_LIMIT_DELAY}")
