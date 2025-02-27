"""Get works from the OpenAlex REST API."""

# Standard library imports
import asyncio
import time
from functools import lru_cache
from itertools import chain
from typing import List, Union, Optional, Any, Dict, Iterator, AsyncIterator

# Third-party imports
from pyalex import Works
from pyalex import Work as PyalexWork
from openalex_types import Work

# Local imports
from .common import OpenAlexError, APIError, RATE_LIMIT_DELAY
from .metrics import metrics_collector
from .wrappers import with_retry
from polus.aithena.common.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=128)
def get_filtered_works(
    filters_tuple: tuple,  # Convert dict to tuple for hashability
    per_page: int = 25,
    max_results: Optional[int] = None,
    cursor_based: bool = True,
    convert_to_model: bool = True,
) -> List[Union[Work, PyalexWork]]:
    """
    Get a list of works filtered by the given criteria.
    Results are cached based on the input parameters.

    Args:
        filters_tuple: Tuple representation of filters dictionary
        per_page: Number of results per page (default: 25)
        max_results: Maximum number of results to return (default: None, returns all)
        cursor_based: Whether to use cursor-based pagination (True) or offset-based (False)
                      Cursor-based is recommended for large result sets (>10,000 items)
        convert_to_model: Whether to convert PyalexWork objects to openalex_types.Work models

    Returns:
        List of Work or PyalexWork objects
    """
    # Convert tuple back to dictionary for use
    filters = dict(filters_tuple)

    # Record cache hit
    metrics_collector.record_request(0, success=True, cached=True)

    logger.info(f"Fetching works with filters: {filters}, max_results: {max_results}")

    try:
        if cursor_based:
            results = list(
                iter_filtered_works_cursor(
                    filters, per_page, max_results, convert_to_model
                )
            )
        else:
            results = list(
                iter_filtered_works_offset(
                    filters, per_page, max_results, convert_to_model
                )
            )

        logger.info(f"Retrieved {len(results)} works")
        return results
    except Exception as e:
        logger.error(f"Error retrieving works: {e}")
        raise OpenAlexError(f"Failed to retrieve works: {str(e)}")


def get_filtered_works_dict(
    filters: Dict[str, Any],
    per_page: int = 25,
    max_results: Optional[int] = None,
    cursor_based: bool = True,
    convert_to_model: bool = True,
) -> List[Union[Work, PyalexWork]]:
    """
    Wrapper around get_filtered_works that accepts a dictionary for filters.
    This function converts the dict to a tuple for caching purposes.

    Args:
        filters: Dictionary of filters to apply
        per_page: Number of results per page (default: 25)
        max_results: Maximum number of results to return (default: None, returns all)
        cursor_based: Whether to use cursor-based pagination
        convert_to_model: Whether to convert PyalexWork objects to models

    Returns:
        List of Work or PyalexWork objects
    """
    # Convert dict to sorted tuple of items for hashability
    filters_tuple = tuple(sorted(filters.items()))
    return get_filtered_works(
        filters_tuple=filters_tuple,
        per_page=per_page,
        max_results=max_results,
        cursor_based=cursor_based,
        convert_to_model=convert_to_model,
    )


def pyalex_to_model(work: PyalexWork) -> Work:
    """
    Convert a PyalexWork object to an openalex_types.Work model.

    Args:
        work: PyalexWork object to convert

    Returns:
        Work model
    """
    try:
        # The work object already contains the data, not need to call get()
        # Just convert it directly to a dictionary
        work_data = work
        # Convert to openalex_types.Work model
        return Work.model_validate(work_data)
    except Exception as e:
        logger.error(f"Error converting PyalexWork to Work model: {e}")
        raise OpenAlexError(f"Model conversion error: {str(e)}")


def _process_work(work: PyalexWork, convert_to_model: bool) -> Union[Work, PyalexWork]:
    """
    Process a work object, optionally converting to a model.
    Centralizes the conversion logic for reuse.

    Args:
        work: The PyalexWork object to process
        convert_to_model: Whether to convert to Work model

    Returns:
        Either the original PyalexWork or a converted Work model
    """
    if convert_to_model:
        return pyalex_to_model(work)
    return work


# Function to validate and sanitize pagination parameters
def _validate_pagination_params(per_page: int, max_results: Optional[int]) -> tuple:
    """
    Validate and sanitize pagination parameters.

    Args:
        per_page: Number of results per page
        max_results: Maximum number of results to return

    Returns:
        Tuple of (per_page, max_results)
    """
    # Ensure per_page is within reasonable bounds
    if per_page < 1:
        logger.warning(f"Invalid per_page value {per_page}, using default of 25")
        per_page = 25
    elif per_page > 200:
        logger.warning(f"per_page value {per_page} exceeds API limit, capping at 200")
        per_page = 200

    # Ensure max_results is valid if specified
    if max_results is not None and max_results < 1:
        logger.warning(f"Invalid max_results value {max_results}, removing limit")
        max_results = None

    return per_page, max_results


@with_retry
def iter_filtered_works_cursor(
    filters: Dict[str, Any],
    per_page: int = 25,
    max_results: Optional[int] = None,
    convert_to_model: bool = False,
) -> Iterator[Union[Work, PyalexWork]]:
    """
    Iterator for works using cursor-based pagination.
    Recommended for large result sets (>10,000 items).

    Args:
        filters: Dictionary of filters to apply
        per_page: Number of results per page (default: 25)
        max_results: Maximum number of results to return (default: None, returns all)
        convert_to_model: Whether to convert PyalexWork objects to openalex_types.Work models

    Yields:
        Individual Work or PyalexWork objects
    """
    per_page, max_results = _validate_pagination_params(per_page, max_results)
    query = Works().filter(**filters)

    # Set n_max to None to retrieve all results, or to a specific number to limit
    n_max = max_results

    try:
        # Use chain to flatten the pages into a single iterator of records
        for i, work in enumerate(
            chain.from_iterable(query.paginate(per_page=per_page, n_max=n_max))
        ):
            if max_results is not None and i >= max_results:
                break

            yield _process_work(work, convert_to_model)
    except Exception as e:
        logger.error(f"Error in cursor-based pagination: {e}")
        raise APIError(f"Pagination error: {str(e)}")


@with_retry
def iter_filtered_works_offset(
    filters: Dict[str, Any],
    per_page: int = 25,
    max_results: Optional[int] = None,
    convert_to_model: bool = False,
) -> Iterator[Union[Work, PyalexWork]]:
    """
    Iterator for works using offset-based pagination.
    Limited to 10,000 results by the OpenAlex API.

    Args:
        filters: Dictionary of filters to apply
        per_page: Number of results per page (default: 25)
        max_results: Maximum number of results to return (default: None, returns all available)
        convert_to_model: Whether to convert PyalexWork objects to openalex_types.Work models

    Yields:
        Individual Work or PyalexWork objects
    """
    per_page, max_results = _validate_pagination_params(per_page, max_results)
    query = Works().filter(**filters)

    # Default to 10000 if max_results is None, as that's the API limit for offset pagination
    # Otherwise use the smaller of max_results or 10000
    limit = min(10000, max_results) if max_results is not None else 10000

    count = 0
    page = 1

    while True:
        try:
            # Get the current page of results
            results = query.get(page=page, per_page=per_page)

            # Stop if no results
            if not results or "results" not in results or not results["results"]:
                break

            # Yield each work in the results
            for work_data in results["results"]:
                count += 1
                if count > limit:
                    return

                work = PyalexWork(work_data)
                yield _process_work(work, convert_to_model)

            # Move to next page
            page += 1

            # Respect rate limits with a small delay between pages
            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            logger.error(f"Error in offset-based pagination at page {page}: {e}")
            raise APIError(f"Pagination error at page {page}: {str(e)}")


@with_retry
def get_works_page(
    filters: Dict[str, Any],
    page: int = 1,
    per_page: int = 25,
    cursor: Optional[str] = None,
    convert_to_model: bool = True,
) -> Dict[str, Any]:
    """
    Get a single page of works.

    Args:
        filters: Dictionary of filters to apply
        page: Page number for offset-based pagination
        per_page: Number of results per page
        cursor: Cursor string for cursor-based pagination
        convert_to_model: Whether to convert results to openalex_types.Work models

    Returns:
        Dictionary containing the page results and metadata
    """
    per_page, _ = _validate_pagination_params(per_page, None)
    query = Works().filter(**filters)

    try:
        if cursor:
            # Cursor-based pagination
            results = query.get(per_page=per_page, cursor=cursor)
        else:
            # Offset-based pagination
            results = query.get(page=page, per_page=per_page)

        # Convert results if requested
        if convert_to_model and "results" in results:
            results["results"] = [
                pyalex_to_model(PyalexWork(work)).model_dump()
                for work in results["results"]
            ]

        return results
    except Exception as e:
        logger.error(f"Error getting works page: {e}")
        raise APIError(f"Failed to get works page: {str(e)}")


# Async implementations for improved performance


async def get_filtered_works_async(
    filters: Dict[str, Any],
    per_page: int = 25,
    max_results: Optional[int] = None,
    convert_to_model: bool = True,
) -> List[Union[Work, PyalexWork]]:
    """
    Asynchronously get a list of works filtered by the given criteria.

    Args:
        filters: Dictionary of filters to apply
        per_page: Number of results per page (default: 25)
        max_results: Maximum number of results to return (default: None, returns all)
        convert_to_model: Whether to convert PyalexWork objects to openalex_types.Work models

    Returns:
        List of Work or PyalexWork objects
    """
    per_page, max_results = _validate_pagination_params(per_page, max_results)
    logger.info(f"Asynchronously fetching works with filters: {filters}")

    start_time = time.time()
    success = True

    try:
        results = [
            work
            async for work in iter_filtered_works_async(
                filters, per_page, max_results, convert_to_model
            )
        ]

        logger.info(f"Asynchronously retrieved {len(results)} works")
        return results
    except Exception as e:
        success = False
        logger.error(f"Error in async retrieval: {e}")
        raise OpenAlexError(f"Failed async retrieval: {str(e)}")
    finally:
        duration_ms = (time.time() - start_time) * 1000
        metrics_collector.record_request(duration_ms, success, cached=False)


async def iter_filtered_works_async(
    filters: Dict[str, Any],
    per_page: int = 25,
    max_results: Optional[int] = None,
    convert_to_model: bool = False,
) -> AsyncIterator[Union[Work, PyalexWork]]:
    """
    Async iterator for works using concurrent requests for improved performance.

    Args:
        filters: Dictionary of filters to apply
        per_page: Number of results per page (default: 25)
        max_results: Maximum number of results to return (default: None, returns all)
        convert_to_model: Whether to convert PyalexWork objects to models

    Yields:
        Individual Work or PyalexWork objects
    """
    per_page, max_results = _validate_pagination_params(per_page, max_results)
    query = Works().filter(**filters)

    # First get metadata to determine total pages
    try:
        first_page = await asyncio.to_thread(query.get, page=1, per_page=1)
        if not first_page or "meta" not in first_page:
            return

        total_count = first_page["meta"]["count"]
        if total_count == 0:
            return

        total_pages = (total_count + per_page - 1) // per_page

        # Limit by max_results if specified
        if max_results is not None:
            total_pages = min(total_pages, (max_results + per_page - 1) // per_page)

        # Limit to 10,000 items (OpenAlex limit for offset pagination)
        total_pages = min(total_pages, 10000 // per_page)

        # Create tasks for each page
        tasks = []
        for page_num in range(1, total_pages + 1):
            tasks.append(
                asyncio.create_task(
                    asyncio.to_thread(query.get, page=page_num, per_page=per_page)
                )
            )

        # Process pages as they complete
        count = 0
        for task_batch in _chunked_tasks(tasks, 5):  # Process 5 concurrent requests
            batch_results = await asyncio.gather(*task_batch)
            for page_results in batch_results:
                if not page_results or "results" not in page_results:
                    continue

                for work_data in page_results["results"]:
                    if max_results is not None and count >= max_results:
                        return

                    work = PyalexWork(work_data)
                    yield _process_work(work, convert_to_model)
                    count += 1

            # Rate limit between batches
            await asyncio.sleep(RATE_LIMIT_DELAY)

    except Exception as e:
        logger.error(f"Error in async pagination: {e}")
        raise APIError(f"Async pagination error: {str(e)}")


def _chunked_tasks(tasks, chunk_size):
    """Helper function to chunk tasks for controlled concurrency"""
    for i in range(0, len(tasks), chunk_size):
        yield tasks[i : i + chunk_size]
