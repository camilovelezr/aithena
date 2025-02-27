from polus.aithena.jobs.getopenalex.oa_rest.api_direct import (
    api_session,
    get_filtered_works_async,
)


# Example of using the improved API with async and metrics
async def fetch_recent_works():
    # Use context manager for proper session handling
    async with api_session():
        # Get works asynchronously
        works = await get_filtered_works_async(
            filters={"from_publication_date": "2023-01-01", "is_open_access": True},
            per_page=100,
            max_results=500,
        )
        # Process works
        for work in works:
            print(work.title)

        # Get performance metrics
        print(metrics.get_summary())


# Run the async function
import asyncio

asyncio.run(fetch_recent_works())
