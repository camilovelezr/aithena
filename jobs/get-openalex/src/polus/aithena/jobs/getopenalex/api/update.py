"""OpenAlex database update jobs.

This module provides functionality to sync a PostgreSQL database with
data from the OpenAlex API. It includes incremental updates based on modification date.
"""

from datetime import datetime, timedelta
import os
import json
from typing import Dict, Optional, Any, Iterator

from openalex_types import Work
from sqlmodel import Session, SQLModel, create_engine, select, col, Field
from pydantic import BaseModel
from sqlalchemy import JSON
from sqlalchemy.sql import text
import psycopg
from psycopg.types.json import Json

from polus.aithena.jobs.getopenalex import iter_filtered_works_cursor
from polus.aithena.jobs.getopenalex.api.logging import JobLogger
from polus.aithena.jobs.getopenalex.api.database import (
    Database,
    JobRepository,
    JobType,
    JobStatus,
    Job,
)
from polus.aithena.jobs.getopenalex.config import DB_CONFIG_STRING, UPDATE_BATCH_SIZE, UPDATE_MAX_RECORDS
from polus.aithena.jobs.getopenalex.rest.get_works import pyalex_to_model
from polus.aithena.common.logger import get_logger

# Set up logger
logger = get_logger(__name__)

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
        postgres_url: str = None,  # Kept for backward compatibility
        job_db: Database = None,
        batch_size: int = None,
        max_records: int = None,
    ):
        # Log the configuration at startup
        logger.info(f"Initializing OpenAlexDBUpdater with DB_CONFIG_STRING: {DB_CONFIG_STRING}")
        
        # PostgreSQL connection - we no longer need to parse URLs, 
        # as we'll use DB_CONFIG_STRING directly
        self.db_config_string = DB_CONFIG_STRING
        
        # Job database - keep SQLAlchemy here since it could be SQLite
        self.job_db = job_db or Database()
        self.job_repo = JobRepository(self.job_db)

        # Configuration
        self.batch_size = batch_size or UPDATE_BATCH_SIZE or DEFAULT_BATCH_SIZE
        self.max_records = max_records or UPDATE_MAX_RECORDS or DEFAULT_MAX_RECORDS

        # Ensure tables exist
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure required tables exist in both databases."""
        # Job database tables - keep SQLAlchemy for this
        self.job_db.create_tables()

        # Print directly to ensure visibility
        print(f"DEBUG: Attempting to connect to PostgreSQL with connection string: {self.db_config_string}")
        logger.info(f"Ensuring PostgreSQL tables exist using: {self.db_config_string}")

        try:
            # Try with localhost IP address if hostname doesn't work
            connection_string = self.db_config_string
            
            # First attempt - with the original connection string
            print(f"DEBUG: First connection attempt with: {connection_string}")
            try:
                # PostgreSQL tables
                with psycopg.connect(connection_string) as conn:
                    print("DEBUG: Successfully connected to PostgreSQL")
                    logger.info("Successfully connected to PostgreSQL")
                    
                    with conn.cursor() as cur:
                        # Check if the openalex.works table exists in the openalex schema (not public)
                        print("DEBUG: Checking if openalex.works table exists")
                        cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'openalex' 
                            AND table_name = 'works'
                        )
                        """)
                        table_exists = cur.fetchone()[0]
                        
                        print(f"DEBUG: openalex.works table exists: {table_exists}")
                        logger.info(f"openalex.works table exists: {table_exists}")
                        
                        if not table_exists:
                            raise ValueError("openalex.works table does not exist")
            except psycopg.OperationalError as e:
                # If the original connection string fails, try with 127.0.0.1 instead of localhost
                if "localhost" in connection_string:
                    fallback_string = connection_string.replace("host=localhost", "host=127.0.0.1")
                    print(f"DEBUG: First connection attempt failed. Trying with 127.0.0.1 instead: {fallback_string}")
                    
                    with psycopg.connect(fallback_string) as conn:
                        print("DEBUG: Successfully connected to PostgreSQL using 127.0.0.1")
                        logger.info("Successfully connected to PostgreSQL using 127.0.0.1")
                        
                        # Save the working connection string for future use
                        self.db_config_string = fallback_string
                        
                        with conn.cursor() as cur:
                            # Check if the openalex.works table exists
                            print("DEBUG: Checking if openalex.works table exists")
                            cur.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'openalex' 
                                AND table_name = 'works'
                            )
                            """)
                            table_exists = cur.fetchone()[0]
                            
                            print(f"DEBUG: openalex.works table exists: {table_exists}")
                            logger.info(f"openalex.works table exists: {table_exists}")
                            
                            if not table_exists:
                                raise ValueError("openalex.works table does not exist")
                else:
                    # If we're not using localhost or the fallback also failed, re-raise
                    raise
        except Exception as e:
            error_msg = f"Failed to connect to PostgreSQL: {e}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            
            # Print network diagnostic information
            import socket
            try:
                hostname = self.db_config_string.split("host=")[1].split(" ")[0]
                print(f"DEBUG: Attempting to resolve hostname: {hostname}")
                ip = socket.gethostbyname(hostname)
                print(f"DEBUG: Resolved {hostname} to {ip}")
            except Exception as e:
                print(f"DEBUG: Could not resolve hostname: {e}")
            
            # Re-raise the exception after logging it
            raise

    def _get_last_update_date(self) -> Optional[str]:
        """Get the last update date from the job history."""
        last_job = self.job_repo.get_last_successful_job(JobType.WORKS_UPDATE)
        if last_job and last_job.parameters.get("from_date"):
            return last_job.parameters["from_date"]

        # Default to 7 days ago if no previous job
        default_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
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
        job_logger = JobLogger(f"works_update_{job.id}")

        try:
            # Start job
            job = self.job_repo.start_job(job.id)
            job_logger.start_job(from_date=from_date)

            # Setup counters
            processed = 0
            created = 0
            updated = 0
            failed = 0

            # Iterate through works
            job_logger.info(f"Starting works update from {from_date}", from_date=from_date)

            # Use cursor-based pagination to iterate through all matching works
            # This is more efficient for large result sets
            for work in self._iterate_works(from_date=from_date, logger=job_logger):
                try:
                    result = self._process_work(work)
                    processed += 1

                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1

                    # Log progress periodically
                    if processed % 100 == 0:
                        job_logger.progress(
                            current=processed,
                            created=created,
                            updated=updated,
                            failed=failed,
                        )

                    # Check if we've reached the maximum
                    if processed >= self.max_records:
                        job_logger.info(
                            f"Reached maximum records limit ({self.max_records})"
                        )
                        break

                except Exception as e:
                    failed += 1
                    # Use dictionary access instead of attribute access since work is now a dict
                    job_logger.error(f"Error processing work: {str(e)}", work_id=work.get("id", "unknown"))

            # Complete job
            status = JobStatus.COMPLETED
            job_logger.info(
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
            job_logger.error(f"Works update failed: {error_message}")

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
        job_logger.end_job(status="success")
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
    ) -> Iterator[Work]:
        """Iterate through works from OpenAlex API.

        Args:
            from_date: From date in ISO format
            logger: JobLogger instance for logging

        Yields:
            Work dictionaries from the API
        """
        # Define filters
        filters = {
            "from_publication_date": from_date,
        }

        logger.info("Starting iteration through works", filters=filters)

        # Use cursor-based pagination for efficiency
        for i, work in enumerate(iter_filtered_works_cursor(filters=filters)):
            # Convert PyAlex Work object to openalex_types.Work model and then to dictionary
            # This ensures proper validation and consistent structure
            work_model = pyalex_to_model(work)
            # work_dict = work_model.model_dump()
            logger.info("Processing work", work_id=work_model.id)
            yield work_model

            # Periodically log progress
            if i > 0 and i % 1000 == 0:
                logger.info(f"Iterated through {i} works so far")

    def _process_work(self, work: Work) -> str:
        """Process a single work record.

        Args:
            work: Work data from OpenAlex API

        Returns:
            String indicating operation: 'created', 'updated', or 'skipped'
        """
        # Convert to a simplified record

        # Use direct psycopg connection for all database operations
        try:
            with psycopg.connect(self.db_config_string) as conn:
                # Create a cursor
                with conn.cursor() as cur:
                    # Check if the work exists in the openalex schema
                    cur.execute("SELECT id FROM openalex.works WHERE id = %s", (work.id,))
                    existing = cur.fetchone()

                    if existing:
                        # Update existing work using direct SQL
                        logger.info(f"Work {work.id} already exists in the database")
                        return "skipped"
               
                    else:
                        # Insert new work record
                        cur.execute(f"INSERT INTO {work._sql_table_name} {work.sql_columns} VALUES {work.sql_values}")
                        conn.commit()
                        return "created"
        except Exception as e:
            logger.error(f"Database error processing work {work.id}: {str(e)}")
            raise


# Convenience function to run an update job
def run_works_update(
    from_date: Optional[str] = None,
    postgres_url: Optional[str] = None,  # Kept for backward compatibility
    job_db_url: Optional[str] = None,
    batch_size: Optional[int] = None,
    max_records: Optional[int] = None,
    job_id: Optional[int] = None,
) -> Job:
    """Run a works update job.

    Args:
        from_date: ISO format date string (YYYY-MM-DD) to start updates from
        postgres_url: PostgreSQL connection URL (deprecated, use DB_CONFIG_STRING in env vars instead)
        job_db_url: Job database connection URL
        batch_size: Number of records to process in a batch
        max_records: Maximum number of records to process
        job_id: Optional existing job ID to use

    Returns:
        The completed job record
    """
    # Setup job database
    job_db = Database(job_db_url) if job_db_url else None

    # Create updater
    updater = OpenAlexDBUpdater(
        postgres_url=postgres_url,  # Will be ignored, using DB_CONFIG_STRING instead
        job_db=job_db,
        batch_size=batch_size,
        max_records=max_records,
    )

    # Run update
    return updater.update_works(from_date=from_date, job_id=job_id)
