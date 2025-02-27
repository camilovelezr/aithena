"""getopenalex module for downloading OpenAlex records from their S3 bucket and interacting with their REST API."""

__version__ = "0.1.0-dev1"

# Re-export key functionality for easier imports
from polus.aithena.jobs.getopenalex.s3 import app as s3_app
from polus.aithena.jobs.getopenalex.rest import (
    # Work retrieval functions
    get_filtered_works,
    get_filtered_works_dict,
    get_filtered_works_async,
    iter_filtered_works_cursor,
    iter_filtered_works_offset,
    iter_filtered_works_async,
    # Pagination utilities
    WorksPaginator,
    PaginatorOptions,
    # Context managers
    api_session,
    async_api_session,
    # Error handling
    OpenAlexError,
    RateLimitError,
    APIError,
    # Metrics collection
    metrics_collector,
)

# Import and export FastAPI application
try:
    from polus.aithena.jobs.getopenalex.api import api_app
except ImportError:
    # FastAPI might not be installed, in which case we set api_app to None
    api_app = None

__all__ = [
    # S3 functionality
    "s3_app",
    # Work retrieval
    "get_filtered_works",
    "get_filtered_works_dict",
    "get_filtered_works_async",
    "iter_filtered_works_cursor",
    "iter_filtered_works_offset",
    "iter_filtered_works_async",
    # Pagination
    "WorksPaginator",
    "PaginatorOptions",
    # Context and sessions
    "api_session",
    "async_api_session",
    # Error handling
    "OpenAlexError",
    "RateLimitError",
    "APIError",
    # Metrics
    "metrics_collector",
    # API
    "api_app",
]
