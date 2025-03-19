"""Database models and utilities for OpenAlex API.

This module provides SQLModel models and database interaction utilities
for tracking job execution history and metadata.
"""

from datetime import datetime, timedelta
from enum import Enum
import os
from typing import Optional, List, Dict, Any, Union
from uuid import uuid4
from datetime import timezone

from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select, delete
from sqlalchemy import JSON

from polus.aithena.common.logger import get_logger
from polus.aithena.jobs.getopenalex.config import JOB_DATABASE_URL

logger = get_logger(__name__)


# Environment variable for job database URL
ENV_JOB_DATABASE_URL = "JOB_DATABASE_URL"

# Connection string will be overridden by environment variable
DEFAULT_DATABASE_URL = "sqlite:///./openalex_jobs.db"


class JobStatus(str, Enum):
    """Status values for job execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class JobType(str, Enum):
    """Types of update jobs."""

    WORKS_UPDATE = "WORKS_UPDATE"
    AUTHORS_UPDATE = "AUTHORS_UPDATE"
    VENUES_UPDATE = "VENUES_UPDATE"
    CONCEPTS_UPDATE = "CONCEPTS_UPDATE"
    INSTITUTIONS_UPDATE = "INSTITUTIONS_UPDATE"
    FULL_UPDATE = "FULL_UPDATE"


class Job(SQLModel, table=True):
    """Job execution metadata for tracking updates."""

    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: JobType = Field(index=True)
    status: JobStatus = Field(default=JobStatus.PENDING, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # Update statistics
    records_processed: int = Field(default=0)
    records_created: int = Field(default=0)
    records_updated: int = Field(default=0)
    records_failed: int = Field(default=0)

    # Additional metadata
    parameters: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    error_message: Optional[str] = Field(default=None)

    # Relationships
    job_logs: List["JobLog"] = Relationship(back_populates="job")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> Optional[float]:
        """Calculate job success rate."""
        total = self.records_processed
        if total > 0:
            return (total - self.records_failed) / total
        return None


class JobLog(SQLModel, table=True):
    """Detailed log entry for job execution."""

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = Field(default="INFO")
    message: str
    details: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # Relationship
    job: Job = Relationship(back_populates="job_logs")


# Database engine and session handling
class Database:
    """Database connection and session management."""

    def __init__(self, database_url: str = None):
        # Use provided URL, config setting, or default
        self.database_url = database_url or JOB_DATABASE_URL or DEFAULT_DATABASE_URL

        # Ensure directory exists for SQLite database if using a file path
        if self.database_url.startswith("sqlite:///"):
            db_path = self.database_url.replace("sqlite:///", "")
            if db_path.startswith("/"):  # Absolute path
                os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Create engine with appropriate configurations
        connect_args = {}
        if self.database_url.startswith("sqlite:"):
            connect_args = {"check_same_thread": False}

        self.engine = create_engine(
            self.database_url, echo=False, connect_args=connect_args
        )
        logger.info(f"Initialized database connection to {self.database_url}")

    def create_tables(self):
        """Create all defined tables in the database."""
        SQLModel.metadata.create_all(self.engine)
        logger.info("Database tables created")

    def get_session(self) -> Session:
        """Get a new database session."""
        return Session(self.engine)


# Job repository for data access
class JobRepository:
    """Data access layer for job metadata."""

    def __init__(self, db: Database):
        self.db = db

    def create_job(self, job_type: JobType, parameters: Dict[str, Any] = None) -> Job:
        """Create a new job."""
        with self.db.get_session() as session:
            job = Job(
                job_type=job_type,
                parameters=parameters or {},
                status=JobStatus.PENDING,
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def get_job(self, job_id: int) -> Optional[Job]:
        """Get a job by ID."""
        with self.db.get_session() as session:
            return session.get(Job, job_id)

    def delete_all_jobs(self) -> int:
        """Delete all jobs and their logs from the database.
        
        Returns:
            The number of deleted jobs
        """
        with self.db.get_session() as session:
            # First delete all logs as they reference jobs
            session.exec(delete(JobLog))
            
            # Then delete all jobs
            deleted_count = session.exec(delete(Job)).rowcount
            session.commit()
            
            logger.info(f"Deleted all {deleted_count} jobs and their logs from the database")
            return deleted_count

    def start_job(self, job_id: int) -> Optional[Job]:
        """Mark a job as started."""
        with self.db.get_session() as session:
            job = session.get(Job, job_id)
            if job:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                session.add(job)
                session.commit()
                session.refresh(job)
                logger.info(
                    f"Started job", extra={"job_id": job.id, "job_type": job.job_type}
                )
                logger.info(job)
            return job

    def complete_job(
        self,
        job_id: int,
        status: JobStatus,
        records_processed: int = 0,
        records_created: int = 0,
        records_updated: int = 0,
        records_failed: int = 0,
        error_message: str = None,
    ) -> Optional[Job]:
        """Mark a job as completed."""
        with self.db.get_session() as session:
            job = session.get(Job, job_id)
            if job:
                job.status = status
                job.completed_at = datetime.utcnow()
                job.records_processed = records_processed
                job.records_created = records_created
                job.records_updated = records_updated
                job.records_failed = records_failed
                job.error_message = error_message

                session.add(job)
                session.commit()
                session.refresh(job)
                logger.info(
                    f"Completed job",
                    extra={
                        "job_id": job.id,
                        "job_type": job.job_type,
                        "status": status,
                        "duration_seconds": job.duration_seconds,
                        "records_processed": records_processed,
                    },
                )
            return job

    def add_log(
        self,
        job_id: int,
        message: str,
        level: str = "INFO",
        details: Dict[str, Any] = None,
    ) -> JobLog:
        """Add a log entry for a job."""
        with self.db.get_session() as session:
            log = JobLog(
                job_id=job_id,
                level=level,
                message=message,
                details=details or {},
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            return log

    def get_job_logs(self, job_id: int) -> List[JobLog]:
        """Get all logs for a job."""
        with self.db.get_session() as session:
            return session.exec(
                select(JobLog).where(JobLog.job_id == job_id).order_by(JobLog.timestamp)
            ).all()

    def get_recent_jobs(self, limit: int = 10) -> List[Job]:
        """Get the most recent jobs."""
        with self.db.get_session() as session:
            return session.exec(
                select(Job).order_by(Job.created_at.desc()).limit(limit)
            ).all()

    def get_jobs_by_status(self, status: JobStatus, limit: int = 100) -> List[Job]:
        """Get jobs by status."""
        with self.db.get_session() as session:
            return session.exec(
                select(Job)
                .where(Job.status == status)
                .order_by(Job.created_at.desc())
                .limit(limit)
            ).all()

    def get_jobs_by_type(self, job_type: JobType, limit: int = 100) -> List[Job]:
        """Get jobs by type."""
        with self.db.get_session() as session:
            return session.exec(
                select(Job)
                .where(Job.job_type == job_type)
                .order_by(Job.created_at.desc())
                .limit(limit)
            ).all()

    def get_last_successful_job(self, job_type: JobType) -> Optional[Job]:
        """Get the last successful job of the given type."""
        with self.db.get_session() as session:
            query = (
                select(Job)
                .where(
                    Job.job_type == job_type,
                    Job.status == JobStatus.COMPLETED,
                )
                .order_by(Job.completed_at.desc())
            )
            result = session.exec(query).first()
            return result

    def abort_all_running_jobs(self) -> int:
        """Abort all jobs that are currently running.
        
        Updates the status of all RUNNING jobs to ABORTED.
        
        Returns:
            The number of jobs that were aborted
        """
        with self.db.get_session() as session:
            # Find all running jobs
            query = select(Job).where(Job.status == JobStatus.RUNNING)
            running_jobs = session.exec(query).all()
            
            # If there are no running jobs, return early
            if not running_jobs:
                logger.info("No running jobs found to abort")
                return 0
            
            # Update each job's status to ABORTED
            aborted_count = 0
            for job in running_jobs:
                job.status = JobStatus.ABORTED
                job.completed_at = datetime.utcnow()
                job.error_message = "Job aborted by user request"
                
                # Add a log entry
                log = JobLog(
                    job_id=job.id,
                    level="WARNING",
                    message="Job aborted by user request",
                    details={"aborted_at": datetime.utcnow().isoformat()}
                )
                session.add(log)
                aborted_count += 1
            
            session.commit()
            logger.info(f"Aborted {aborted_count} running jobs")
            return aborted_count
