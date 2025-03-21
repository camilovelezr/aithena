"""Common RabbitMQ utilities."""

from pydantic import BaseModel, Field, UUID4
import datetime
from faststream.rabbit import RabbitExchange, RabbitQueue, ExchangeType
from typing import Optional

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

ask_aithena_exchange = RabbitExchange(
    "ask-aithena-exchange",
    ExchangeType.TOPIC,
    durable=True,
)

ask_aithena_queue = RabbitQueue(
    "ask-aithena-queue",
    routing_key="session.{session_id}",
)


class ProcessingStatus(BaseModel):
    """Status message for query processing."""

    # session_id: UUID4 = Field(..., description="Unique identifier for the session")
    timestamp: str = Field(
        ...,
        description="Timestamp of the status update",
        default_factory=lambda: datetime.datetime.now().isoformat(),
    )
    status: str = Field(..., description="Current processing status")
    message: Optional[str] = Field(None, description="Current processing message")
