import uuid

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from sqlalchemy.exc import SQLAlchemyError

from app.services.document_status_service import (
    DOCUMENT_STATUSES,
    DocumentStatusNotFoundError,
    DocumentStatusPersistenceError,
    InvalidDocumentStatusError,
    InvalidStatusTransitionError,
    can_retry_document,
    get_document_processing_status,
    is_document_completed,
    is_document_failed,
    is_document_processing,
    transition_document_status,
    validate_document_status,
    validate_status_transition,
)


@pytest.fixture
def document_id():
    return uuid.uuid4()


@pytest.fixture
def document_record(document_id):
    return SimpleNamespace(
        id=document_id,
        processing_status="pending",
        processing_started_at=None,
        processing_completed_at=None,
        processing_attempts=0,
        processing_error=None,
        page_count=None,
    )


@pytest.fixture
def db(document_record):
    session = MagicMock()
    session.scalar.return_value = document_record
    session.get.return_value = document_record
    return session


# ============================================================
# STATUS VALIDATION
# ============================================================

def test_document_status_definitions():
    assert DOCUMENT_STATUSES == {
        "pending",
        "processing",
        "completed",
        "failed",
    }


@pytest.mark.parametrize(
    "status",
    ["pending", "processing", "completed", "failed"],
)
def test_valid_document_status(status):
    validate_document_status(status)


def test_invalid_document_status():
    with pytest.raises(InvalidDocumentStatusError):
        validate_document_status("unknown")


# ============================================================
# TRANSITION VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "current,new",
    [
        ("pending", "processing"),
        ("processing", "completed"),
        ("processing", "failed"),
        ("failed", "processing"),
    ],
)
def test_allowed_status_transitions(current, new):
    validate_status_transition(current, new)


@pytest.mark.parametrize(
    "current,new",
    [
        ("pending", "completed"),
        ("pending", "failed"),
        ("processing", "pending"),
        ("completed", "processing"),
        ("completed", "failed"),
        ("failed", "completed"),
    ],
)
def test_rejected_status_transitions(current, new):
    with pytest.raises(InvalidStatusTransitionError):
        validate_status_transition(current, new)


# ============================================================
# PROCESSING TRANSITION
# ============================================================

def test_pending_to_processing(db, document_id, document_record):
    result = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    assert result.processing_status == "processing"
    assert result.processing_started_at is not None
    assert result.processing_completed_at is None
    assert result.processing_attempts == 1
    assert result.processing_error is None

    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_failed_document_can_restart_processing(
    db,
    document_id,
    document_record,
):
    document_record.processing_status = "failed"
    document_record.processing_attempts = 2
    document_record.processing_error = "Previous error"

    result = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    assert result.processing_status == "processing"
    assert result.processing_attempts == 3
    assert result.processing_error is None
    assert result.processing_started_at is not None
    assert result.processing_completed_at is None


# ============================================================
# COMPLETION TRANSITION
# ============================================================

def test_processing_to_completed(
    db,
    document_id,
    document_record,
):
    document_record.processing_status = "processing"

    result = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="completed",
        page_count=12,
    )

    assert result.processing_status == "completed"
    assert result.processing_completed_at is not None
    assert result.page_count == 12
    assert result.processing_error is None


def test_completed_without_page_count(
    db,
    document_id,
    document_record,
):
    document_record.processing_status = "processing"

    result = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="completed",
    )

    assert result.processing_status == "completed"


def test_completed_rejects_invalid_page_count(
    db,
    document_id,
    document_record,
):
    document_record.processing_status = "processing"

    with pytest.raises(ValueError):
        transition_document_status(
            db=db,
            document_id=document_id,
            new_status="completed",
            page_count=0,
        )


# ============================================================
# FAILURE TRANSITION
# ============================================================

def test_processing_to_failed(
    db,
    document_id,
    document_record,
):
    document_record.processing_status = "processing"

    result = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="failed",
        error_message="OCR processing failed.",
    )

    assert result.processing_status == "failed"
    assert result.processing_completed_at is not None
    assert result.processing_error == "OCR processing failed."


def test_failed_requires_error_message(
    db,
    document_id,
    document_record,
):
    document_record.processing_status = "processing"

    with pytest.raises(ValueError):
        transition_document_status(
            db=db,
            document_id=document_id,
            new_status="failed",
        )


def test_failed_error_message_is_limited(
    db,
    document_id,
    document_record,
):
    document_record.processing_status = "processing"

    result = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="failed",
        error_message="x" * 3000,
    )

    assert len(result.processing_error) == 2000


# ============================================================
# DATABASE TRANSACTION HANDLING
# ============================================================

def test_database_error_rolls_back(
    db,
    document_id,
    document_record,
):
    db.commit.side_effect = SQLAlchemyError(
        "Database failure"
    )

    with pytest.raises(DocumentStatusPersistenceError):
        transition_document_status(
            db=db,
            document_id=document_id,
            new_status="processing",
        )

    db.rollback.assert_called_once()


def test_missing_document(db, document_id):
    db.scalar.return_value = None

    with pytest.raises(DocumentStatusNotFoundError):
        transition_document_status(
            db=db,
            document_id=document_id,
            new_status="processing",
        )

    db.commit.assert_not_called()


def test_invalid_transition_rolls_back(
    db,
    document_id,
    document_record,
):
    document_record.processing_status = "completed"

    with pytest.raises(InvalidStatusTransitionError):
        transition_document_status(
            db=db,
            document_id=document_id,
            new_status="processing",
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_invalid_document_uuid():
    db = MagicMock()

    with pytest.raises(ValueError):
        transition_document_status(
            db=db,
            document_id="invalid",
            new_status="processing",
        )


# ============================================================
# STATUS RETRIEVAL
# ============================================================

def test_get_document_processing_status(
    db,
    document_id,
    document_record,
):
    document_record.processing_status = "completed"
    document_record.processing_attempts = 2
    document_record.page_count = 8

    result = get_document_processing_status(
        db=db,
        document_id=document_id,
    )

    assert result["document_id"] == str(document_id)
    assert result["processing_status"] == "completed"
    assert result["processing_attempts"] == 2
    assert result["page_count"] == 8


def test_get_status_for_missing_document(db, document_id):
    db.get.return_value = None

    with pytest.raises(DocumentStatusNotFoundError):
        get_document_processing_status(
            db=db,
            document_id=document_id,
        )


# ============================================================
# STATUS HELPERS
# ============================================================

def test_is_document_processing(document_record):
    document_record.processing_status = "processing"

    assert is_document_processing(document_record)


def test_is_document_completed(document_record):
    document_record.processing_status = "completed"

    assert is_document_completed(document_record)


def test_is_document_failed(document_record):
    document_record.processing_status = "failed"

    assert is_document_failed(document_record)


def test_can_retry_failed_document(document_record):
    document_record.processing_status = "failed"

    assert can_retry_document(document_record)


def test_cannot_retry_completed_document(document_record):
    document_record.processing_status = "completed"

    assert not can_retry_document(document_record)