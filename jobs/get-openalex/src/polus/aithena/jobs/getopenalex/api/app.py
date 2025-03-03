"""FastAPI application for OpenAlex REST API operations."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os

from polus.aithena.common.logger import get_logger
from polus.aithena.jobs.getopenalex import (
    get_filtered_works_async,
    WorksPaginator,
    OpenAlexError,
    RateLimitError,
    APIError,
)

from polus.aithena.jobs.getopenalex.api.database import (
    Database,
    JobRepository,
    JobType,
    JobStatus,
    Job as DBJob,
)
from polus.aithena.jobs.getopenalex.api.update import run_works_update

logger = get_logger(__name__)

# Initialize database
db = Database()
job_repo = JobRepository(db)

# Create database tables
try:
    db.create_tables()
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")

app = FastAPI(
    title="OpenAlex API",
    description="API for querying OpenAlex academic data and managing database updates",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class WorkSearchParams(BaseModel):
    """Parameters for searching works."""

    query: Optional[str] = Field(None, description="Search query")
    from_date: Optional[str] = Field(
        None, description="From publication date (YYYY-MM-DD)"
    )
    to_date: Optional[str] = Field(None, description="To publication date (YYYY-MM-DD)")
    limit: int = Field(10, description="Maximum number of results", ge=1, le=100)
    page: int = Field(1, description="Page number", ge=1)
    per_page: int = Field(10, description="Results per page", ge=1, le=100)
    author_id: Optional[str] = Field(None, description="Filter by author ID")
    institution_id: Optional[str] = Field(None, description="Filter by institution ID")
    venue_id: Optional[str] = Field(None, description="Filter by venue ID")
    concept_id: Optional[str] = Field(None, description="Filter by concept ID")

    def to_filters(self) -> Dict[str, Any]:
        """Convert search parameters to OpenAlex API filters."""
        filters = {}
        if self.from_date:
            filters["from_publication_date"] = self.from_date
        if self.to_date:
            filters["to_publication_date"] = self.to_date
        if self.author_id:
            filters["author.id"] = self.author_id
        if self.institution_id:
            filters["institutions.id"] = self.institution_id
        if self.venue_id:
            filters["host_venue.id"] = self.venue_id
        if self.concept_id:
            filters["concepts.id"] = self.concept_id
        return filters


class PaginatedResponse(BaseModel):
    """Base model for paginated responses."""

    count: int
    next_page: Optional[int] = None
    prev_page: Optional[int] = None
    current_page: int
    total_pages: Optional[int] = None
    results: List[Dict[str, Any]]


class Job(BaseModel):
    """Job model for API responses."""

    id: int
    job_type: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_failed: int = 0
    parameters: Dict[str, Any] = {}
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None

    @classmethod
    def from_db_job(cls, db_job: DBJob) -> "Job":
        """Convert a database job to an API job."""
        return cls(
            id=db_job.id,
            job_type=db_job.job_type.value,
            status=db_job.status.value,
            created_at=db_job.created_at,
            started_at=db_job.started_at,
            completed_at=db_job.completed_at,
            records_processed=db_job.records_processed,
            records_created=db_job.records_created,
            records_updated=db_job.records_updated,
            records_failed=db_job.records_failed,
            parameters=db_job.parameters,
            error_message=db_job.error_message,
            duration_seconds=db_job.duration_seconds,
        )


class UpdateRequest(BaseModel):
    """Request to start a data update job."""

    job_type: str = Field(..., description="Type of update job")
    from_date: Optional[str] = Field(
        None, description="Start date for updates (YYYY-MM-DD)"
    )
    max_records: Optional[int] = Field(None, description="Maximum records to process")


class JobLogEntry(BaseModel):
    """Job log entry for API responses."""

    id: int
    job_id: int
    timestamp: datetime
    level: str
    message: str
    details: Dict[str, Any] = {}


# Routes
@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "OpenAlex API",
        "version": "0.1.0",
        "description": "API for querying OpenAlex academic data and managing database updates",
        "endpoints": [
            "/works",
            "/works/search",
            "/works/{work_id}",
            "/health",
            "/jobs",
            "/jobs/{job_id}",
            "/jobs/{job_id}/logs",
            "/update",
            "/docs",
        ],
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/works", response_model=PaginatedResponse)
async def get_works(
    query: Optional[str] = Query(None, description="Search query"),
    from_date: Optional[str] = Query(
        None, description="From publication date (YYYY-MM-DD)"
    ),
    to_date: Optional[str] = Query(
        None, description="To publication date (YYYY-MM-DD)"
    ),
    author_id: Optional[str] = Query(None, description="Filter by author ID"),
    institution_id: Optional[str] = Query(None, description="Filter by institution ID"),
    venue_id: Optional[str] = Query(None, description="Filter by venue ID"),
    concept_id: Optional[str] = Query(None, description="Filter by concept ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Results per page"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
):
    """Get works from OpenAlex with various filters."""
    search_params = WorkSearchParams(
        query=query,
        from_date=from_date,
        to_date=to_date,
        author_id=author_id,
        institution_id=institution_id,
        venue_id=venue_id,
        concept_id=concept_id,
        page=page,
        per_page=per_page,
        limit=limit,
    )

    filters = search_params.to_filters()
    logger.info(f"Searching works with query='{query}' and filters={filters}")

    try:
        paginator = WorksPaginator(
            search=query,
            filters=filters,
            per_page=per_page,
            initial_page=page,
        )

        results_page = await paginator.get_page_async()
        results = [work.model_dump() for work in results_page]

        response = PaginatedResponse(
            count=paginator.count if paginator.count else len(results),
            current_page=paginator.current_page,
            next_page=paginator.current_page + 1 if paginator.has_next else None,
            prev_page=(
                paginator.current_page - 1 if paginator.current_page > 1 else None
            ),
            total_pages=paginator.total_pages,
            results=results[:limit],  # Apply limit
        )

        return response

    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {str(e)}")
        raise HTTPException(status_code=429, detail="OpenAlex rate limit exceeded")
    except APIError as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"OpenAlex API error: {str(e)}")
    except OpenAlexError as e:
        logger.error(f"OpenAlex error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenAlex error: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")


@app.post("/works/search", response_model=PaginatedResponse)
async def search_works(search_params: WorkSearchParams):
    """Search for works with a request body."""
    filters = search_params.to_filters()
    logger.info(
        f"Searching works with query='{search_params.query}' and filters={filters}"
    )

    try:
        paginator = WorksPaginator(
            search=search_params.query,
            filters=filters,
            per_page=search_params.per_page,
            initial_page=search_params.page,
        )

        results_page = await paginator.get_page_async()
        results = [work.model_dump() for work in results_page]

        response = PaginatedResponse(
            count=paginator.count if paginator.count else len(results),
            current_page=paginator.current_page,
            next_page=paginator.current_page + 1 if paginator.has_next else None,
            prev_page=(
                paginator.current_page - 1 if paginator.current_page > 1 else None
            ),
            total_pages=paginator.total_pages,
            results=results[: search_params.limit],  # Apply limit
        )

        return response

    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {str(e)}")
        raise HTTPException(status_code=429, detail="OpenAlex rate limit exceeded")
    except APIError as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"OpenAlex API error: {str(e)}")
    except OpenAlexError as e:
        logger.error(f"OpenAlex error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenAlex error: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")


@app.get("/works/{work_id}")
async def get_work_by_id(work_id: str):
    """Get a specific work by ID."""
    try:
        # Format the work ID if needed (e.g., adding prefix)
        if not work_id.startswith("https://openalex.org/"):
            formatted_id = f"https://openalex.org/{work_id}"
        else:
            formatted_id = work_id

        works = await get_filtered_works_async(filters={"id": formatted_id}, max_results=1)

        if not works:
            raise HTTPException(
                status_code=404, detail=f"Work with ID {work_id} not found"
            )

        return works[0].model_dump()

    except HTTPException:
        raise
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {str(e)}")
        raise HTTPException(status_code=429, detail="OpenAlex rate limit exceeded")
    except APIError as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"OpenAlex API error: {str(e)}")
    except OpenAlexError as e:
        logger.error(f"OpenAlex error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenAlex error: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")


# Job management endpoints
@app.get("/jobs", response_model=List[Job])
async def get_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of jobs to return"
    ),
):
    """Get a list of jobs."""
    try:
        if status:
            try:
                status_enum = JobStatus(status.upper())
                jobs = job_repo.get_jobs_by_status(status_enum, limit=limit)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values are: {', '.join([s.value for s in JobStatus])}",
                )
        elif job_type:
            try:
                job_type_enum = JobType(job_type.upper())
                jobs = job_repo.get_jobs_by_type(job_type_enum, limit=limit)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid job type: {job_type}. Valid values are: {', '.join([t.value for t in JobType])}",
                )
        else:
            jobs = job_repo.get_recent_jobs(limit=limit)

        return [Job.from_db_job(job) for job in jobs]

    except Exception as e:
        logger.exception(f"Error retrieving jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving jobs: {str(e)}")


@app.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: int):
    """Get a specific job by ID."""
    job = job_repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    return Job.from_db_job(job)


@app.get("/jobs/{job_id}/logs", response_model=List[JobLogEntry])
async def get_job_logs(job_id: int):
    """Get logs for a specific job."""
    job = job_repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")

    logs = job_repo.get_job_logs(job_id)
    return [
        JobLogEntry(
            id=log.id,
            job_id=log.job_id,
            timestamp=log.timestamp,
            level=log.level,
            message=log.message,
            details=log.details,
        )
        for log in logs
    ]


# Update job endpoints
def run_update_job_background(
    job_type: str, from_date: Optional[str] = None, max_records: Optional[int] = None
):
    """Run an update job in the background."""
    try:
        if job_type.upper() == JobType.WORKS_UPDATE.value:
            run_works_update(from_date=from_date, max_records=max_records)
        else:
            logger.error(f"Unsupported job type: {job_type}")
    except Exception as e:
        logger.exception(f"Error running update job: {str(e)}")


@app.post("/update", response_model=Job)
async def start_update_job(
    update_request: UpdateRequest, background_tasks: BackgroundTasks
):
    """Start a data update job."""
    try:
        # Validate job type
        try:
            job_type_enum = JobType(update_request.job_type.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid job type: {update_request.job_type}. Valid values are: {', '.join([t.value for t in JobType])}",
            )

        # Currently only supporting WORKS_UPDATE
        if job_type_enum != JobType.WORKS_UPDATE:
            raise HTTPException(
                status_code=400,
                detail=f"Currently only {JobType.WORKS_UPDATE.value} is supported",
            )

        # Create job
        job = job_repo.create_job(
            job_type=job_type_enum,
            parameters={
                "from_date": update_request.from_date,
                "max_records": update_request.max_records,
            },
        )

        # Start job in background
        background_tasks.add_task(
            run_update_job_background,
            job_type=job_type_enum.value,
            from_date=update_request.from_date,
            max_records=update_request.max_records,
        )

        return Job.from_db_job(job)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting update job: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error starting update job: {str(e)}"
        )
