import errno
import uuid

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from sqlalchemy.exc import OperationalError

from app.services import document_status_service
from app.services.document_status_service import (
    DocumentAlreadyClaimedError,
    InvalidStatusTransitionError,
    claim_document_for_processing,
)

from app.services.document_error_service import (
    DocumentErrorCategory,
    classify_document_error,
    is_retryable_document_error,
)

from app.services.document_processing_service import (
    DocumentProcessingAlreadyClaimedError,
)

from app.services.document_retry_service import (
    process_document_with_retries,
)

from app.core.retry_config import DocumentRetrySettings

from app.services.ocr_service import OCRProcessingError


# ==========================================================
# SHARED FIXTURES
# ==========================================================

@pytest.fixture
def retry_settings():
    return DocumentRetrySettings(
        enabled=True,
        max_attempts=3,
        initial_delay_seconds=5.0,
        backoff_multiplier=2.0,
        max_delay_seconds=60.0,
    )


@pytest.fixture
def document_record():
    return SimpleNamespace(
        id=uuid.uuid4(),
        processing_status="pending",
        processing_attempts=0,
    )


@pytest.fixture
def processing_arguments(
    document_record,
    tmp_path,
):
    return {
        "document_record": document_record,
        "pdf_path": tmp_path / "sample.pdf",
        "db": MagicMock(),
        "document_settings": MagicMock(),
        "ocr_settings": MagicMock(),
    }


# ==========================================================
# ATOMIC DOCUMENT CLAIM TESTS
# ==========================================================

def test_claim_document_successfully(
    monkeypatch,
    document_record,
):
    expected_document = document_record

    def mock_transition(**kwargs):
        assert kwargs["new_status"] == "processing"
        assert kwargs["document_id"] == document_record.id

        return expected_document

    monkeypatch.setattr(
        document_status_service,
        "transition_document_status",
        mock_transition,
    )

    result = claim_document_for_processing(
        db=MagicMock(),
        document_id=document_record.id,
    )

    assert result is expected_document


def test_claim_document_rejects_already_claimed_document(
    monkeypatch,
    document_record,
):
    def mock_transition(**kwargs):
        raise InvalidStatusTransitionError(
            "Document is already processing."
        )

    monkeypatch.setattr(
        document_status_service,
        "transition_document_status",
        mock_transition,
    )

    with pytest.raises(DocumentAlreadyClaimedError):

        claim_document_for_processing(
            db=MagicMock(),
            document_id=document_record.id,
        )


def test_claim_document_preserves_database_errors(
    monkeypatch,
    document_record,
):
    def mock_transition(**kwargs):
        raise document_status_service.DocumentStatusPersistenceError(
            "Database unavailable."
        )

    monkeypatch.setattr(
        document_status_service,
        "transition_document_status",
        mock_transition,
    )

    with pytest.raises(
        document_status_service.DocumentStatusPersistenceError
    ):

        claim_document_for_processing(
            db=MagicMock(),
            document_id=document_record.id,
        )


# ==========================================================
# ERROR CLASSIFICATION TESTS
# ==========================================================

@pytest.mark.parametrize(
    "exception",
    [
        TimeoutError("Temporary timeout."),
        ConnectionError("Temporary connection failure."),
        OSError(
            errno.ECONNRESET,
            "Connection reset.",
        ),
    ],
)
def test_transient_errors_are_retryable(exception):

    classification = classify_document_error(exception)

    assert classification.category == (
        DocumentErrorCategory.TRANSIENT
    )

    assert classification.retryable is True


@pytest.mark.parametrize(
    "sqlstate",
    [
        "40001",
        "40P01",
        "55P03",
        "57P01",
        "57P02",
        "57P03",
        "08006",
        "08001",
    ],
)
def test_transient_postgresql_errors_are_retryable(sqlstate):

    original_error = SimpleNamespace(
        sqlstate=sqlstate,
        pgcode=None,
    )

    exception = OperationalError(
        "Database operation failed.",
        {},
        original_error,
    )

    classification = classify_document_error(exception)

    assert classification.category == (
        DocumentErrorCategory.TRANSIENT
    )

    assert classification.retryable is True


def test_unknown_postgresql_operational_error_is_not_retryable():

    original_error = SimpleNamespace(
        sqlstate="23505",
        pgcode=None,
    )

    exception = OperationalError(
        "Unique constraint violation.",
        {},
        original_error,
    )

    classification = classify_document_error(exception)

    assert classification.category == (
        DocumentErrorCategory.PERMANENT
    )

    assert classification.retryable is False


@pytest.mark.parametrize(
    "exception",
    [
        ValueError("Invalid document."),
        TypeError("Invalid input."),
        FileNotFoundError("PDF not found."),
        PermissionError("Access denied."),
    ],
)
def test_permanent_errors_are_not_retryable(exception):

    classification = classify_document_error(exception)

    assert classification.category == (
        DocumentErrorCategory.PERMANENT
    )

    assert classification.retryable is False


def test_wrapped_transient_error_is_detected():

    try:
        try:
            raise TimeoutError("Temporary timeout.")

        except TimeoutError as original:
            raise OCRProcessingError(
                "OCR processing failed."
            ) from original

    except OCRProcessingError as exception:

        classification = classify_document_error(exception)

    assert classification.retryable is True


def test_unknown_error_defaults_to_permanent():

    classification = classify_document_error(
        RuntimeError("Unexpected failure.")
    )

    assert classification.category == (
        DocumentErrorCategory.PERMANENT
    )

    assert classification.retryable is False


def test_retryable_helper_matches_classification():

    assert is_retryable_document_error(
        TimeoutError("Temporary timeout.")
    )

    assert not is_retryable_document_error(
        ValueError("Invalid PDF.")
    )


# ==========================================================
# DUPLICATE WORKER PROTECTION TESTS
# ==========================================================

def test_already_claimed_document_is_not_retried(
    processing_arguments,
    retry_settings,
    monkeypatch,
):
    calls = []
    delays = []

    def mock_process_document(**kwargs):
        calls.append(1)

        raise DocumentProcessingAlreadyClaimedError(
            "Another worker owns this document."
        )

    monkeypatch.setattr(
        "app.services.document_retry_service.process_document",
        mock_process_document,
    )

    with pytest.raises(DocumentProcessingAlreadyClaimedError):

        process_document_with_retries(
            **processing_arguments,
            retry_settings=retry_settings,
            sleep_function=delays.append,
        )

    assert len(calls) == 1
    assert delays == []


def test_already_claimed_document_does_not_consume_retry_attempts(
    processing_arguments,
    retry_settings,
    monkeypatch,
):
    document = processing_arguments["document_record"]

    original_attempts = document.processing_attempts

    def mock_process_document(**kwargs):
        raise DocumentProcessingAlreadyClaimedError(
            "Document already claimed."
        )

    monkeypatch.setattr(
        "app.services.document_retry_service.process_document",
        mock_process_document,
    )

    with pytest.raises(DocumentProcessingAlreadyClaimedError):

        process_document_with_retries(
            **processing_arguments,
            retry_settings=retry_settings,
            sleep_function=lambda delay: None,
        )

    assert document.processing_attempts == original_attempts


# ==========================================================
# RETRY SETTINGS VALIDATION TESTS
# ==========================================================

def test_retry_settings_max_attempts(retry_settings):

    assert retry_settings.max_attempts == 3


def test_retry_settings_initial_delay(retry_settings):

    assert retry_settings.initial_delay_seconds == 5.0


def test_retry_settings_backoff_multiplier(retry_settings):

    assert retry_settings.backoff_multiplier == 2.0


def test_retry_settings_maximum_delay(retry_settings):

    assert retry_settings.max_delay_seconds == 60.0