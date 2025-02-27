"""OpenAlex database update jobs.

This module provides functionality to sync a PostgreSQL database with
data from the OpenAlex API. It includes incremental updates based on modification date.
"""

from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional, Any, Tuple, Iterator
import time

from sqlmodel import Session, SQLModel, create_engine, select, col
from pydantic import BaseModel

from polus.aithena.jobs.getopenalex import (
    get_filtered_works,
    iter_filtered_works_cursor,
    WorksPaginator,
    OpenAlexError,
)
from polus.aithena.jobs.getopenalex.api.logging import JobLogger
from polus.aithena.jobs.getopenalex.api.database import (
    Database,
    JobRepository,
    JobType,
    JobStatus,
    Job,
)


# Default PostgreSQL connection string - should be overridden by environment variables
DEFAULT_POSTGRES_URL = "postgresql://postgres:postgres@localhost:5432/openalex"

# Environment variable names
ENV_POSTGRES_URL = "OPENALEX_POSTGRES_URL"
ENV_BATCH_SIZE = "OPENALEX_UPDATE_BATCH_SIZE"
ENV_MAX_RECORDS = "OPENALEX_UPDATE_MAX_RECORDS"

# Default values
DEFAULT_BATCH_SIZE = 100
DEFAULT_MAX_RECORDS = 10000


class WorkRecord(BaseModel):
    """Simplified OpenAlex work record for database operations."""

    id: str
    title: str
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    updated_date: Optional[str] = None

    @classmethod
    def from_openalex(cls, work_data: Dict[str, Any]) -> "WorkRecord":
        """Create a WorkRecord from OpenAlex API data."""
        return cls(
            id=work_data.get("id", ""),
            title=work_data.get("title", ""),
            publication_date=work_data.get("publication_date"),
            doi=work_data.get("doi"),
            updated_date=work_data.get("updated_date"),
        )


class OpenAlexDBUpdater:
    """Update a PostgreSQL database with data from OpenAlex API."""

    def __init__(
        self,
        postgres_url: str = None,
        job_db: Database = None,
        batch_size: int = None,
        max_records: int = None,
    ):
        # PostgreSQL connection
        self.postgres_url = postgres_url or os.getenv(
            ENV_POSTGRES_URL, DEFAULT_POSTGRES_URL
        )
        self.pg_engine = create_engine(self.postgres_url, echo=False)

        # Job database
        self.job_db = job_db or Database()
        self.job_repo = JobRepository(self.job_db)

        # Configuration
        self.batch_size = batch_size or int(
            os.getenv(ENV_BATCH_SIZE, DEFAULT_BATCH_SIZE)
        )
        self.max_records = max_records or int(
            os.getenv(ENV_MAX_RECORDS, DEFAULT_MAX_RECORDS)
        )

        # Ensure tables exist
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure required tables exist in both databases."""
        # Job database tables
        self.job_db.create_tables()

        # PostgreSQL tables - create if they don't exist
        # Define models for the PostgreSQL database tables
        class Work(SQLModel, table=True):
            __tablename__ = "openalex_works"

            id: str = Field(primary_key=True)
            title: str
            publication_date: Optional[str] = Field(default=None, index=True)
            doi: Optional[str] = Field(default=None, index=True)
            updated_date: Optional[str] = Field(default=None, index=True)
            data: Dict[str, Any] = Field(default_factory=dict)
            last_updated: datetime = Field(default_factory=datetime.utcnow)

        # Create tables if they don't exist
        SQLModel.metadata.create_all(self.pg_engine)

    def _get_last_update_date(self) -> Optional[str]:
        """Get the last update date from the job history."""
        last_job = self.job_repo.get_last_successful_job(JobType.WORKS_UPDATE)
        if last_job and last_job.parameters.get("from_date"):
            return last_job.parameters["from_date"]

        # Default to 7 days ago if no previous job
        default_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        return default_date

    def update_works(
        self, from_date: Optional[str] = None, job_id: Optional[int] = None
    ) -> Job:
        """Update works in the database from the OpenAlex API.

        Args:
            from_date: ISO format date string (YYYY-MM-DD) to start updates from
            job_id: Optional existing job ID to use

        Returns:
            The completed job record
        """
        # Determine from_date if not provided
        if not from_date:
            from_date = self._get_last_update_date()

        # Create or get job
        if job_id:
            job = self.job_repo.get_job(job_id)
            if not job:
                raise ValueError(f"Job with ID {job_id} not found")
        else:
            job = self.job_repo.create_job(
                job_type=JobType.WORKS_UPDATE,
                parameters={"from_date": from_date},
            )

        # Logger
        logger = JobLogger(f"works_update_{job.id}")

        try:
            # Start job
            job = self.job_repo.start_job(job.id)
            logger.start_job(from_date=from_date)

            # Setup counters
            processed = 0
            created = 0
            updated = 0
            failed = 0

            # Iterate through works
            logger.info(f"Starting works update from {from_date}", from_date=from_date)

            # Use cursor-based pagination to iterate through all matching works
            # This is more efficient for large result sets
            for work in self._iterate_works(from_date=from_date, logger=logger):
                try:
                    result = self._process_work(work)
                    processed += 1

                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1

                    # Log progress periodically
                    if processed % 100 == 0:
                        logger.progress(
                            current=processed,
                            created=created,
                            updated=updated,
                            failed=failed,
                        )

                    # Check if we've reached the maximum
                    if processed >= self.max_records:
                        logger.info(
                            f"Reached maximum records limit ({self.max_records})"
                        )
                        break

                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing work: {str(e)}", work_id=work.id)

            # Complete job
            status = JobStatus.COMPLETED
            logger.info(
                f"Works update completed: {processed} processed, {created} created, {updated} updated, {failed} failed",
                processed=processed,
                created=created,
                updated=updated,
                failed=failed,
            )

        except Exception as e:
            # Handle job failure
            status = JobStatus.FAILED
            error_message = str(e)
            logger.error(f"Works update failed: {error_message}")

            # Complete the job with failure status
            return self.job_repo.complete_job(
                job_id=job.id,
                status=status,
                records_processed=processed if "processed" in locals() else 0,
                records_created=created if "created" in locals() else 0,
                records_updated=updated if "updated" in locals() else 0,
                records_failed=failed if "failed" in locals() else 0,
                error_message=error_message,
            )

        # Complete the job with success status
        logger.end_job(status="success")
        return self.job_repo.complete_job(
            job_id=job.id,
            status=status,
            records_processed=processed,
            records_created=created,
            records_updated=updated,
            records_failed=failed,
        )

    def _iterate_works(
        self, from_date: str, logger: JobLogger
    ) -> Iterator[Dict[str, Any]]:
        """Iterate through works from OpenAlex API.

        Args:
            from_date: From date in ISO format
            logger: JobLogger instance for logging

        Yields:
            Work dictionaries from the API
        """
        # Define filters
        filters = {
            "from_updated_date": from_date,
        }

        logger.info("Starting iteration through works", filters=filters)

        # Use cursor-based pagination for efficiency
        for i, work in enumerate(iter_filtered_works_cursor(filters=filters)):
            # Convert to dict for processing
            yield work.model_dump()

            # Periodically log progress
            if i > 0 and i % 1000 == 0:
                logger.info(f"Iterated through {i} works so far")

    def _process_work(self, work_data: Dict[str, Any]) -> str:
        """Process a single work record.

        Args:
            work_data: Work data from OpenAlex API

        Returns:
            String indicating operation: 'created', 'updated', or 'skipped'
        """
        # Convert to a simplified record
        work_record = WorkRecord.from_openalex(work_data)

        # Check if work exists in database
        with Session(self.pg_engine) as session:
            # Check if work exists
            stmt = (
                select(SQLModel)
                .where(col("id") == work_record.id)
                .select_from(SQLModel.metadata.tables["openalex_works"])
            )
            existing_work = session.exec(stmt).first()

            if existing_work:
                # Update existing work
                for field, value in work_record.model_dump().items():
                    setattr(existing_work, field, value)

                # Update full data JSON and timestamp
                existing_work.data = work_data
                existing_work.last_updated = datetime.utcnow()

                session.add(existing_work)
                session.commit()
                return "updated"
            else:
                # Create new work
                # Need to use raw SQL to insert due to dynamic table
                from sqlalchemy import insert

                stmt = insert(SQLModel.metadata.tables["openalex_works"]).values(
                    id=work_record.id,
                    title=work_record.title,
                    publication_date=work_record.publication_date,
                    doi=work_record.doi,
                    updated_date=work_record.updated_date,
                    data=work_data,
                    last_updated=datetime.utcnow(),
                )
                session.execute(stmt)
                session.commit()
                return "created"


# Convenience function to run an update job
def run_works_update(
    from_date: Optional[str] = None,
    postgres_url: Optional[str] = None,
    job_db_url: Optional[str] = None,
    batch_size: Optional[int] = None,
    max_records: Optional[int] = None,
) -> Job:
    """Run a works update job.

    Args:
        from_date: ISO format date string (YYYY-MM-DD) to start updates from
        postgres_url: PostgreSQL connection URL
        job_db_url: Job database connection URL
        batch_size: Number of records to process in a batch
        max_records: Maximum number of records to process

    Returns:
        The completed job record
    """
    # Setup job database
    job_db = Database(job_db_url) if job_db_url else None

    # Create updater
    updater = OpenAlexDBUpdater(
        postgres_url=postgres_url,
        job_db=job_db,
        batch_size=batch_size,
        max_records=max_records,
    )

    # Run update
    return updater.update_works(from_date=from_date)
