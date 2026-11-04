import logging

import pytest

from app.services.document_observability_service import (
    DocumentObservability,
    document_observability,
    observe_processing_stage,
)


@pytest.fixture
def observer():

    return DocumentObservability()


@pytest.fixture(autouse=True)
def reset_global_metrics():

    document_observability.reset()

    yield

    document_observability.reset()


def test_initial_metrics_are_zero(observer):

    result = observer.snapshot()

    assert result["processing"]["started"] == 0
    assert result["processing"]["completed"] == 0
    assert result["processing"]["failed"] == 0

    assert result["stages"] == {}


def test_processing_started_counter(observer):

    observer.record_processing_started(
        document_id="test-document",
        attempt=1,
    )

    result = observer.snapshot()

    assert result["processing"]["started"] == 1


def test_processing_completed_counter(observer):

    observer.record_processing_completed(
        document_id="test-document",
        duration_seconds=2.5,
        page_count=4,
        attempt=1,
    )

    result = observer.snapshot()

    assert result["processing"]["completed"] == 1


def test_processing_failed_counter(observer):

    observer.record_processing_failed(
        document_id="test-document",
        stage="ocr_processing",
        error_type="OCRProcessingError",
        attempt=1,
    )

    result = observer.snapshot()

    assert result["processing"]["failed"] == 1


def test_stage_execution_metrics(observer):

    observer.record_stage(
        stage="native_extraction",
        duration_seconds=2.0,
    )

    result = observer.snapshot()

    metric = result["stages"]["native_extraction"]

    assert metric["executions"] == 1
    assert metric["failures"] == 0
    assert metric["total_duration_seconds"] == 2.0
    assert metric["average_duration_seconds"] == 2.0


def test_stage_maximum_duration(observer):

    observer.record_stage(
        "ocr_processing",
        2.0,
    )

    observer.record_stage(
        "ocr_processing",
        5.0,
    )

    result = observer.snapshot()

    metric = result["stages"]["ocr_processing"]

    assert metric["maximum_duration_seconds"] == 5.0
    assert metric["executions"] == 2


def test_stage_failure_counter(observer):

    observer.record_stage(
        "ocr_processing",
        1.5,
        failed=True,
    )

    result = observer.snapshot()

    metric = result["stages"]["ocr_processing"]

    assert metric["failures"] == 1


def test_failed_stage_context_records_failure():

    with pytest.raises(ValueError):

        with observe_processing_stage(
            "test-document",
            "native_extraction",
        ):

            raise ValueError("Test failure")

    result = document_observability.snapshot()

    metric = result["stages"]["native_extraction"]

    assert metric["executions"] == 1
    assert metric["failures"] == 1


def test_successful_stage_context_records_execution():

    with observe_processing_stage(
        "test-document",
        "text_cleaning",
    ):

        value = 10 + 5

    assert value == 15

    result = document_observability.snapshot()

    metric = result["stages"]["text_cleaning"]

    assert metric["executions"] == 1
    assert metric["failures"] == 0


def test_stage_context_preserves_original_exception():

    expected = ValueError("Original error")

    with pytest.raises(ValueError) as captured:

        with observe_processing_stage(
            "test-document",
            "ocr_processing",
        ):

            raise expected

    assert captured.value is expected


def test_snapshot_average_duration(observer):

    observer.record_stage(
        "chunking",
        2.0,
    )

    observer.record_stage(
        "chunking",
        4.0,
    )

    result = observer.snapshot()

    metric = result["stages"]["chunking"]

    assert metric["average_duration_seconds"] == 3.0


def test_reset_clears_metrics(observer):

    observer.record_processing_started(
        "test-document",
        1,
    )

    observer.reset()

    result = observer.snapshot()

    assert result["processing"]["started"] == 0
    assert result["stages"] == {}


def test_observability_emits_structured_log(observer, caplog):

    with caplog.at_level(
        logging.INFO,
        logger="scholarai.document.observability",
    ):

        observer.record_processing_started(
            document_id="test-document",
            attempt=1,
        )

    assert any(
        getattr(record, "event", None)
        == "document_processing_started"
        for record in caplog.records
    )


def test_metrics_are_independent_between_instances():

    first = DocumentObservability()
    second = DocumentObservability()

    first.record_processing_started(
        "document-one",
        1,
    )

    assert first.snapshot()["processing"]["started"] == 1

    assert second.snapshot()["processing"]["started"] == 0