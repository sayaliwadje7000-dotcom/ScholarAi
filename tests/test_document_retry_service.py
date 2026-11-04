import uuid

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.retry_config import DocumentRetrySettings

from app.services.document_retry_service import (
    RetryLimitExceededError,
    can_retry_document,
    calculate_retry_delay,
    process_document_with_retries,
)

from app.services.document_error_service import (
    DocumentErrorCategory,
)

from app.services.ocr_service import OCRProcessingError


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


# ============================================================
# BACKOFF TESTS
# ============================================================

def test_first_retry_delay(retry_settings):

    assert calculate_retry_delay(
        1,
        retry_settings,
    ) == 5.0


def test_second_retry_delay(retry_settings):

    assert calculate_retry_delay(
        2,
        retry_settings,
    ) == 10.0


def test_third_retry_delay_is_capped(retry_settings):

    assert calculate_retry_delay(
        3,
        retry_settings,
    ) == 20.0


def test_retry_delay_respects_maximum(retry_settings):

    assert calculate_retry_delay(
        10,
        retry_settings,
    ) == 60.0


def test_invalid_attempt_number(retry_settings):

    with pytest.raises(ValueError):

        calculate_retry_delay(
            0,
            retry_settings,
        )


# ============================================================
# ELIGIBILITY TESTS
# ============================================================

def test_failed_document_can_retry(
    document_record,
    retry_settings,
):

    document_record.processing_status = "failed"
    document_record.processing_attempts = 1

    assert can_retry_document(
        document_record,
        retry_settings,
    )


def test_completed_document_cannot_retry(
    document_record,
    retry_settings,
):

    document_record.processing_status = "completed"

    assert not can_retry_document(
        document_record,
        retry_settings,
    )


def test_exhausted_document_cannot_retry(
    document_record,
    retry_settings,
):

    document_record.processing_status = "failed"
    document_record.processing_attempts = 3

    assert not can_retry_document(
        document_record,
        retry_settings,
    )


# ============================================================
# RETRY EXECUTION TESTS
# ============================================================

def test_successful_first_attempt(
    processing_arguments,
    retry_settings,
    monkeypatch,
):

    expected_result = object()

    def mock_process_document(**kwargs):
        return expected_result

    monkeypatch.setattr(
        "app.services.document_retry_service.process_document",
        mock_process_document,
    )

    result = process_document_with_retries(
        **processing_arguments,
        retry_settings=retry_settings,
    )

    assert result is expected_result


def test_transient_error_retries_successfully(
    processing_arguments,
    retry_settings,
    monkeypatch,
):

    calls = []
    delays = []

    def mock_process_document(**kwargs):

        document = kwargs["document_record"]

        calls.append(1)

        document.processing_attempts += 1

        if len(calls) == 1:

            document.processing_status = "failed"

            raise OCRProcessingError(
                "Temporary OCR failure."
            ) from TimeoutError(
                "Temporary timeout."
            )

        document.processing_status = "completed"

        return "success"

    monkeypatch.setattr(
        "app.services.document_retry_service.process_document",
        mock_process_document,
    )

    result = process_document_with_retries(
        **processing_arguments,
        retry_settings=retry_settings,
        sleep_function=delays.append,
    )

    assert result == "success"
    assert len(calls) == 2
    assert delays == [5.0]


def test_permanent_error_is_not_retried(
    processing_arguments,
    retry_settings,
    monkeypatch,
):

    calls = []

    def mock_process_document(**kwargs):

        calls.append(1)

        raise ValueError(
            "Invalid document."
        )

    monkeypatch.setattr(
        "app.services.document_retry_service.process_document",
        mock_process_document,
    )

    with pytest.raises(ValueError):

        process_document_with_retries(
            **processing_arguments,
            retry_settings=retry_settings,
            sleep_function=lambda delay: None,
        )

    assert len(calls) == 1


def test_retry_limit_is_enforced(
    processing_arguments,
    retry_settings,
    monkeypatch,
):

    calls = []
    delays = []

    def mock_process_document(**kwargs):

        document = kwargs["document_record"]

        calls.append(1)

        document.processing_attempts += 1
        document.processing_status = "failed"

        raise OCRProcessingError(
            "Temporary OCR failure."
        ) from TimeoutError(
            "Temporary timeout."
        )

    monkeypatch.setattr(
        "app.services.document_retry_service.process_document",
        mock_process_document,
    )

    with pytest.raises(RetryLimitExceededError):

        process_document_with_retries(
            **processing_arguments,
            retry_settings=retry_settings,
            sleep_function=delays.append,
        )

    assert len(calls) == 3
    assert delays == [5.0, 10.0]


def test_retry_disabled(
    processing_arguments,
    retry_settings,
    monkeypatch,
):

    calls = []

    disabled_settings = DocumentRetrySettings(
        enabled=False,
        max_attempts=3,
        initial_delay_seconds=5.0,
        backoff_multiplier=2.0,
        max_delay_seconds=60.0,
    )

    def mock_process_document(**kwargs):

        calls.append(1)

        raise OCRProcessingError(
            "Temporary OCR failure."
        ) from TimeoutError(
            "Temporary timeout."
        )

    monkeypatch.setattr(
        "app.services.document_retry_service.process_document",
        mock_process_document,
    )

    with pytest.raises(OCRProcessingError):

        process_document_with_retries(
            **processing_arguments,
            retry_settings=disabled_settings,
        )

    assert len(calls) == 1


def test_existing_attempts_count_toward_limit(
    processing_arguments,
    retry_settings,
):

    document = processing_arguments["document_record"]

    document.processing_attempts = 3
    document.processing_status = "failed"

    with pytest.raises(RetryLimitExceededError):

        process_document_with_retries(
            **processing_arguments,
            retry_settings=retry_settings,
        )