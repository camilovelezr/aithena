"""Paginator for the OpenAlex REST API."""

# Standard library imports
import time
from typing import Any, Dict, Iterator, List, Optional, Union, Annotated, AsyncIterator

# Third-party imports
from pydantic import BaseModel, Field, ConfigDict
from pyalex import Works
from pyalex import Work as PyalexWork
from openalex_types import Work

# Local imports
from .common import APIError, RATE_LIMIT_DELAY
from .get_works import (
    iter_filtered_works_async,
    iter_filtered_works_cursor,
    iter_filtered_works_offset,
    pyalex_to_model,
    get_filtered_works_dict_async,
)
from .metrics import metrics_collector
from polus.aithena.common.logger import get_logger

logger = get_logger(__name__)


# Create a Pydantic model for pagination options
class PaginatorOptions(BaseModel):
    """
    Configuration options for pagination.
    """

    filters: Dict[str, Any]
    per_page: Annotated[int, Field(ge=1, le=200)] = 25
    max_results: Optional[int] = None
    cursor_based: bool = True
    convert_to_model: bool = True
    async_enabled: bool = False
    collect_metrics: bool = True

    model_config = ConfigDict(
        extra="forbid",  # Prevent extra fields
    )


class WorksPaginator(BaseModel):
    """
    Class to handle pagination of works with both cursor and offset-based methods.
    """

    options: PaginatorOptions
    current_page: int = 1
    count: Optional[int] = None
    has_next: bool = True
    search: Optional[str] = None  # Add search as a public field

    # Use ConfigDict for Pydantic v2
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Private attribute for query - won't be included in serialization
    _query: Optional[Any] = None

    def __init__(self, **data):
        # If individual parameters are provided, convert them to options
        if "options" not in data and "filters" in data:
            options_data = {}
            for field in PaginatorOptions.model_fields:
                if field in data:
                    options_data[field] = data.pop(field)
            data["options"] = PaginatorOptions(**options_data)
        
        # Handle initial_page parameter if provided
        if "initial_page" in data:
            data["current_page"] = data.pop("initial_page")

        super().__init__(**data)
        
        # Initialize query with filters
        self._query = Works().filter(**self.options.filters)
        
        # Add search parameter if provided
        if self.search:
            self._query = self._query.search(self.search)

    @property
    def query(self):
        """Access the query object"""
        if self._query is None:
            self._query = Works().filter(**self.options.filters)
            if self.search:
                self._query = self._query.search(self.search)
        return self._query

    @property
    def filters(self) -> Dict[str, Any]:
        """Access filters from options"""
        return self.options.filters

    @property
    def per_page(self) -> int:
        """Access per_page from options"""
        return self.options.per_page

    @property
    def max_results(self) -> Optional[int]:
        """Access max_results from options"""
        return self.options.max_results

    @property
    def cursor_based(self) -> bool:
        """Access cursor_based from options"""
        return self.options.cursor_based

    @property
    def convert_to_model(self) -> bool:
        """Access convert_to_model from options"""
        return self.options.convert_to_model

    @property
    def async_enabled(self) -> bool:
        """Access async_enabled from options"""
        return self.options.async_enabled

    @property
    def collect_metrics(self) -> bool:
        """Access collect_metrics from options"""
        return self.options.collect_metrics

    @property
    def total_pages(self) -> Optional[int]:
        """
        Calculate the total number of pages based on the count and per_page.
        
        Returns:
            Optional[int]: The total number of pages, or None if count is not available
        """
        if self.count is None:
            return None
        
        return (self.count + self.per_page - 1) // self.per_page

    def __iter__(self) -> Iterator[Union[Work, PyalexWork]]:
        """
        Iterate over all works matching the filters.

        Returns:
            Iterator yielding individual works
        """
        if self.cursor_based:
            yield from iter_filtered_works_cursor(
                self.filters, self.per_page, self.max_results, self.convert_to_model
            )
        else:
            yield from iter_filtered_works_offset(
                self.filters, self.per_page, self.max_results, self.convert_to_model
            )

    async def iter_async(self) -> AsyncIterator[Union[Work, PyalexWork]]:
        """
        Asynchronously iterate over all works matching the filters.

        Returns:
            Async iterator yielding individual works
        """
        async for work in iter_filtered_works_async(
            self.filters, self.per_page, self.max_results, self.convert_to_model
        ):
            yield work

    def iter_pages(self) -> Iterator[List[Union[Work, PyalexWork]]]:
        """
        Iterate over pages of works.

        Returns:
            Iterator yielding lists of works, where each list is a page
        """
        if self.cursor_based:
            # Use the paginate method for cursor-based pagination
            for page in self.query.paginate(
                per_page=self.per_page, n_max=self.max_results
            ):
                if self.convert_to_model:
                    yield [pyalex_to_model(work) for work in page]
                else:
                    yield page
        else:
            # Implement offset-based pagination manually
            page_num = 1
            total_yielded = 0

            while True:
                try:
                    results = self.query.get(page=page_num, per_page=self.per_page)

                    if (
                        not results
                        or "results" not in results
                        or not results["results"]
                    ):
                        break

                    if self.convert_to_model:
                        page_items = [
                            pyalex_to_model(PyalexWork(work))
                            for work in results["results"]
                        ]
                    else:
                        page_items = [PyalexWork(work) for work in results["results"]]

                    yield page_items

                    total_yielded += len(page_items)
                    if (
                        self.max_results is not None
                        and total_yielded >= self.max_results
                    ):
                        break

                    page_num += 1

                    # Respect rate limits
                    time.sleep(RATE_LIMIT_DELAY)

                except Exception as e:
                    logger.error(f"Error in paginator at page {page_num}: {e}")
                    raise APIError(f"Pagination error at page {page_num}: {str(e)}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the paginator and its metrics

        Returns:
            Dictionary with paginator info and metrics
        """
        summary = {
            "filters": self.filters,
            "per_page": self.per_page,
            "max_results": self.max_results,
            "cursor_based": self.cursor_based,
            "convert_to_model": self.convert_to_model,
            "async_enabled": self.async_enabled,
        }

        if self.collect_metrics:
            summary["metrics"] = metrics_collector.get_summary()

        return summary

    async def get_page_async(self) -> List[Union[Work, PyalexWork]]:
        """
        Asynchronously get a single page of works.
        
        Returns:
            List of works for the current page
        """
        # Get works for the current page
        result = await get_filtered_works_dict_async(
            self.filters, 
            page=self.current_page, 
            per_page=self.per_page,
            api_key=None,  # Use default API key
            search=self.search
        )
        
        # Update pagination information
        if result and "meta" in result:
            meta = result["meta"]
            self.count = meta.get("count")
            self.has_next = bool(meta.get("next_cursor") or 
                               (meta.get("page") and meta.get("per_page") and 
                                meta.get("count") and 
                                meta.get("page") * meta.get("per_page") < meta.get("count")))
        else:
            self.has_next = False
            
        # Process works
        works = []
        if result and "results" in result and result["results"]:
            if self.convert_to_model:
                works = [pyalex_to_model(PyalexWork(work)) for work in result["results"]]
            else:
                works = [PyalexWork(work) for work in result["results"]]
                
        # Track metrics if enabled
        if self.collect_metrics:
            metrics_collector.api_calls += 1
            metrics_collector.results_retrieved += len(works)
            
        return works
