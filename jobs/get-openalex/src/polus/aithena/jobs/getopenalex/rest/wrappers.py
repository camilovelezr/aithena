"""Wrappers for the OpenAlex REST API."""

# Standard library imports
import time
from typing import Callable, TypeVar

# Third-party imports
import httpx

# Local imports
from .common import OpenAlexError, APIError, MAX_RETRIES
from .metrics import metrics_collector
from polus.aithena.common.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def with_metrics(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to track metrics for a function.

    Args:
        func: Function to decorate

    Returns:
        Decorated function with metrics tracking
    """

    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        cached = False

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.record_request(duration_ms, success, cached)

    return wrapper


def with_retry(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to retry API calls with exponential backoff.

    Args:
        func: Function to decorate

    Returns:
        Decorated function with retry logic
    """

    @with_metrics
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except (httpx.HTTPError, APIError) as e:
                wait_time = 2**retries
                logger.warning(f"API call failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                retries += 1
        # If we get here, all retries failed
        raise OpenAlexError(f"Failed after {MAX_RETRIES} retries")

    return wrapper
