import logging
import uuid

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document import Document


logger = logging.getLogger(__name__)


# ============================================================
# STATUS DEFINITIONS
# ============================================================

DOCUMENT_STATUSES = {
    "pending",
    "processing",
    "completed",
    "failed",
}

ALLOWED_TRANSITIONS = {
    "pending": {"processing"},
    "processing": {"completed", "failed"},
    "completed": set(),
    "failed": {"processing"},
}


# ============================================================
# EXCEPTIONS
# ============================================================

class DocumentStatusError(Exception):
    """Base exception for document status operations."""


class InvalidDocumentStatusError(DocumentStatusError):
    """Raised when a requested status is invalid."""


class InvalidStatusTransitionError(DocumentStatusError):
    """Raised when a status transition is not permitted."""


class DocumentStatusPersistenceError(DocumentStatusError):
    """Raised when a status update cannot be persisted."""


class DocumentStatusNotFoundError(DocumentStatusError):
    """Raised when the requested document does not exist."""


# ============================================================
# TIME HELPER
# ============================================================

def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


# ============================================================
# STATUS VALIDATION
# ============================================================

def validate_document_status(status: str) -> None:
    """Validate a document processing status."""

    if status not in DOCUMENT_STATUSES:
        raise InvalidDocumentStatusError(
            f"Unsupported document status: {status}"
        )


def validate_status_transition(
    current_status: str,
    new_status: str,
) -> None:
    """Validate whether a document can move to a new status."""

    validate_document_status(current_status)
    validate_document_status(new_status)

    allowed = ALLOWED_TRANSITIONS[current_status]

    if new_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Transition from '{current_status}' "
            f"to '{new_status}' is not permitted."
        )


# ============================================================
# DOCUMENT RETRIEVAL
# ============================================================

def _get_locked_document(
    db: Session,
    document_id: uuid.UUID,
) -> Document:
    """
    Retrieve a document while acquiring a row-level lock.

    The lock protects concurrent status transitions on
    databases that support SELECT FOR UPDATE.
    """

    statement = (
        select(Document)
        .where(Document.id == document_id)
        .with_for_update()
    )

    document = db.scalar(statement)

    if document is None:
        raise DocumentStatusNotFoundError(
            "The requested document was not found."
        )

    return document


# ============================================================
# STATUS TRANSITION
# ============================================================

def transition_document_status(
    *,
    db: Session,
    document_id: uuid.UUID,
    new_status: str,
    error_message: str | None = None,
    page_count: int | None = None,
) -> Document:
    """
    Safely transition a document to a new processing status.

    Supported transitions:

        pending -> processing
        processing -> completed
        processing -> failed
        failed -> processing

    Status changes and timestamps are persisted in PostgreSQL.
    """

    if not isinstance(document_id, uuid.UUID):
        raise ValueError("A valid document UUID is required.")

    validate_document_status(new_status)

    if new_status == "failed":
        if not isinstance(error_message, str) or not error_message.strip():
            raise ValueError(
                "A failure description is required."
            )

        error_message = error_message.strip()[:2000]

    elif error_message is not None:
        raise ValueError(
            "Error messages are only permitted for failed status."
        )

    if new_status == "completed":
        if page_count is not None and page_count <= 0:
            raise ValueError(
                "Page count must be greater than zero."
            )

    elif page_count is not None:
        raise ValueError(
            "Page count can only be updated when processing completes."
        )

    try:
        document = _get_locked_document(
            db,
            document_id,
        )

        validate_status_transition(
            document.processing_status,
            new_status,
        )

        now = utc_now()

        if new_status == "processing":
            document.processing_started_at = now
            document.processing_completed_at = None
            document.processing_error = None
            document.processing_attempts = (
                document.processing_attempts or 0
            ) + 1

        elif new_status == "completed":
            document.processing_completed_at = now
            document.processing_error = None

            if page_count is not None:
                document.page_count = page_count

        elif new_status == "failed":
            document.processing_completed_at = now
            document.processing_error = error_message

        document.processing_status = new_status

        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(
            "Document %s transitioned to %s.",
            document_id,
            new_status,
        )

        return document

    except DocumentStatusError:
        db.rollback()
        raise

    except SQLAlchemyError as exc:
        db.rollback()

        logger.exception(
            "Unable to persist document status for %s.",
            document_id,
        )

        raise DocumentStatusPersistenceError(
            "Unable to update document processing status."
        ) from exc


# ============================================================
# STATUS RETRIEVAL
# ============================================================

def get_document_processing_status(
    *,
    db: Session,
    document_id: uuid.UUID,
) -> dict:
    """Return the processing status and lifecycle metadata."""

    document = db.get(
        Document,
        document_id,
    )

    if document is None:
        raise DocumentStatusNotFoundError(
            "The requested document was not found."
        )

    return {
        "document_id": str(document.id),
        "processing_status": document.processing_status,
        "processing_started_at": document.processing_started_at,
        "processing_completed_at": document.processing_completed_at,
        "processing_attempts": document.processing_attempts,
        "processing_error": document.processing_error,
        "page_count": document.page_count,
    }


# ============================================================
# STATUS SUMMARY
# ============================================================

def is_document_processing(document: Document) -> bool:
    """Check whether a document is currently processing."""

    return document.processing_status == "processing"


def is_document_completed(document: Document) -> bool:
    """Check whether document processing succeeded."""

    return document.processing_status == "completed"


def is_document_failed(document: Document) -> bool:
    """Check whether document processing failed."""

    return document.processing_status == "failed"


def can_retry_document(document: Document) -> bool:
    """Check whether a document is eligible for retry."""

    return document.processing_status == "failed"