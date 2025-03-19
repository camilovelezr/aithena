"""Common RabbitMQ utilities."""

from pydantic import BaseModel, Field, UUID4
import datetime

STAGES = {
    "owl": [
        "analyzing_query",
        "finding_relevant_documents",
        "preparing_response",
    ],
    "shield": [
        "analyzing_query",
        "finding_relevant_documents",
        "analyzing_retrieved_documents",
        "ensuring_relevance",
        "preparing_response",
    ],
    "aegis": [
        "analyzing_query",
        "finding_relevant_documents",
        "analyzing_retrieved_documents",
        "individual_check_for_relevance",
        "preparing_response",
    ],
}


class ProcessingStatus(BaseModel):
    """Status message for query processing."""

    session_id: UUID4 = Field(..., description="Unique identifier for the session")
    timestamp: str = Field(
        ...,
        description="Timestamp of the status update",
        default_factory=lambda: datetime.datetime.now().isoformat(),
    )
    stage: str = Field(..., description="Current processing stage")
