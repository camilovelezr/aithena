"""Context managers for the OpenAlex REST API."""

# Standard library imports
import contextlib

# Local imports
from .metrics import metrics_collector
from polus.aithena.common.logger import get_logger

logger = get_logger(__name__)


@contextlib.contextmanager
def api_session(collect_metrics: bool = True):
    """
    Context manager for API sessions with optional metrics collection.

    Args:
        collect_metrics: Whether to collect performance metrics

    Yields:
        None
    """
    if collect_metrics:
        metrics_collector.start_session()

    try:
        yield
    finally:
        if collect_metrics:
            metrics_collector.end_session()
            metrics_collector.log_summary()


@contextlib.asynccontextmanager
async def async_api_session(collect_metrics: bool = True):
    """
    Async context manager for API sessions with optional metrics collection.

    Args:
        collect_metrics: Whether to collect performance metrics

    Yields:
        None
    """
    if collect_metrics:
        metrics_collector.start_session()

    try:
        yield
    finally:
        if collect_metrics:
            metrics_collector.end_session()
            metrics_collector.log_summary()
