"""OpenAlex REST API client modules.

This package provides a modular interface for accessing the OpenAlex REST API.
It includes pagination, caching, metrics collection, and other utilities.
"""

# Import and re-export functionality from common
from .common import (
    OpenAlexError,
    RateLimitError,
    APIError,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RATE_LIMIT_DELAY,
)

# Import and re-export metrics functionality
from .metrics import metrics_collector

# Import and re-export context managers
from .context import api_session, async_api_session

# Import and re-export wrapper functions
from .wrappers import with_metrics, with_retry

# Import and re-export work functions
from .get_works import (
    get_filtered_works,
    get_filtered_works_dict,
    pyalex_to_model,
    get_works_page,
    get_filtered_works_async,
    iter_filtered_works_cursor,
    iter_filtered_works_offset,
    iter_filtered_works_async,
)

# Import and re-export paginator classes
from .paginator import PaginatorOptions, WorksPaginator

__all__ = [
    # Common
    "OpenAlexError",
    "RateLimitError",
    "APIError",
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES",
    "RATE_LIMIT_DELAY",
    # Metrics
    "metrics_collector",
    # Context managers
    "api_session",
    "async_api_session",
    # Wrappers
    "with_metrics",
    "with_retry",
    # Work functions
    "get_filtered_works",
    "get_filtered_works_dict",
    "pyalex_to_model",
    "get_works_page",
    "get_filtered_works_async",
    "iter_filtered_works_cursor",
    "iter_filtered_works_offset",
    "iter_filtered_works_async",
    # Paginator
    "PaginatorOptions",
    "WorksPaginator",
]
