"""Metrics tracking for the OpenAlex REST API."""

# Standard library imports
import statistics
from datetime import datetime
from typing import Any, Dict

# Local imports
from polus.aithena.common.logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """
    Collect and report performance metrics for OpenAlex API calls.
    """

    def __init__(self):
        self.request_times = []
        self.total_requests = 0
        self.failed_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.start_time = None
        self.end_time = None

    def start_session(self):
        """Start a new metrics collection session"""
        self.request_times = []
        self.total_requests = 0
        self.failed_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.start_time = datetime.now()

    def end_session(self):
        """End the current metrics collection session"""
        self.end_time = datetime.now()

    def record_request(self, duration_ms, success=True, cached=False):
        """Record a single API request"""
        self.request_times.append(duration_ms)
        self.total_requests += 1
        if not success:
            self.failed_requests += 1
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the collected metrics"""
        if not self.request_times:
            return {"total_requests": 0, "message": "No requests recorded"}

        total_duration = (
            (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        )

        return {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "success_rate": (
                (self.total_requests - self.failed_requests) / self.total_requests
                if self.total_requests > 0
                else 0
            ),
            "cache_hit_rate": (
                self.cache_hits / self.total_requests if self.total_requests > 0 else 0
            ),
            "avg_request_time_ms": (
                statistics.mean(self.request_times) if self.request_times else 0
            ),
            "median_request_time_ms": (
                statistics.median(self.request_times) if self.request_times else 0
            ),
            "min_request_time_ms": min(self.request_times) if self.request_times else 0,
            "max_request_time_ms": max(self.request_times) if self.request_times else 0,
            "total_duration_seconds": total_duration,
            "requests_per_second": (
                self.total_requests / total_duration if total_duration > 0 else 0
            ),
        }

    def log_summary(self):
        """Log a summary of the metrics"""
        summary = self.get_summary()
        if summary.get("total_requests", 0) > 0:
            logger.info(f"OpenAlex API Metrics: {summary}")


# Create a singleton metrics collector
metrics_collector = MetricsCollector()
