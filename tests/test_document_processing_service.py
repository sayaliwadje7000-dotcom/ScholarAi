import json
from app.services.ocr_service import OCRPageResult
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock, patch

import pytest
from unittest.mock import patch
from app.core.document_config import load_document_settings
from app.core.ocr_config import OCRSettings

from app.services.document_processing_service import (
    DocumentProcessingError,
    DocumentProcessingDatabaseError,
    process_document,
)
@pytest.fixture(autouse=True)
def mock_document_structure_extraction():
    with patch(
        "app.services.document_processing_service.process_document_structure",
        return_value=({}, None),
    ):
        yield

@pytest.fixture
def document_settings(tmp_path):

    return replace(
        load_document_settings(),
        storage_root=tmp_path,
        max_pages=10,
    )


@pytest.fixture
def ocr_settings():

    return OCRSettings(
        tesseract_cmd="tesseract.exe",
        language="eng",
        dpi=300,
        timeout_seconds=60,
        minimum_confidence=40,
        force_ocr=False,
    )


@pytest.fixture
def document_record():

    return SimpleNamespace(
        id=uuid4(),
        page_count=None,
        processing_status="pending",
    )


@pytest.fixture
def db_session():

    return MagicMock()


@pytest.fixture
def pdf_file(tmp_path):

    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-test")

    return path


def create_mock_results(document_id):

    native_page = SimpleNamespace(
        page_number=1,
        text="Native text.",
    )

    native_result = SimpleNamespace(
        document_id=document_id,
        page_count=1,
        pages=[native_page],
    )

    ocr_page = OCRPageResult(
    page_number=1,
    text="Native text.",
    extraction_method="native",
    ocr_status="not_required",
    character_count=12,
    word_count=2,
    average_confidence=None,
    low_confidence=False,
    warnings=[],
)
    ocr_result = SimpleNamespace(
        document_id=document_id,
        page_count=1,
        pages_with_text=1,
        total_characters=12,
        total_words=2,
        average_ocr_confidence=None,
        quality_status="good",
        ocr_pages=[],
        failed_pages=[],
        warnings=[],
        pages=[ocr_page],
    )

    return native_result, ocr_result


def test_process_document_success(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):

    native_result, ocr_result = create_mock_results(
        str(document_record.id)
    )

    with patch(
        "app.services.document_processing_service.extract_pdf_text",
        return_value=native_result,
    ), patch(
        "app.services.document_processing_service.extract_pdf_with_ocr",
        return_value=ocr_result,
    ):

        result = process_document(
            document_record=document_record,
            pdf_path=pdf_file,
            db=db_session,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )

    assert result.processing_status == "completed"
    assert result.page_count == 1
    assert result.total_words == 2
    assert result.quality_status == "good"

    assert document_record.processing_status == "completed"
    assert document_record.page_count == 1

    assert Path(result.artifact_path).exists()

    db_session.commit.assert_called()


def test_unified_artifact_generation(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):

    native_result, ocr_result = create_mock_results(
        str(document_record.id)
    )

    with patch(
        "app.services.document_processing_service.extract_pdf_text",
        return_value=native_result,
    ), patch(
        "app.services.document_processing_service.extract_pdf_with_ocr",
        return_value=ocr_result,
    ):

        result = process_document(
            document_record=document_record,
            pdf_path=pdf_file,
            db=db_session,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )

    artifact = json.loads(
        Path(result.artifact_path).read_text(
            encoding="utf-8"
        )
    )

    assert artifact["document_id"] == str(document_record.id)
    assert artifact["processing_status"] == "completed"
    assert artifact["page_count"] == 1
    assert artifact["pages"][0]["text"] == "Native text."


def test_missing_pdf(
    document_record,
    db_session,
    tmp_path,
    document_settings,
    ocr_settings,
):

    with pytest.raises(DocumentProcessingError):

        process_document(
            document_record=document_record,
            pdf_path=tmp_path / "missing.pdf",
            db=db_session,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )


def test_native_extraction_failure(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):

    with patch(
        "app.services.document_processing_service.extract_pdf_text",
        side_effect=Exception("Extraction failed"),
    ):

        with pytest.raises(DocumentProcessingError):

            process_document(
                document_record=document_record,
                pdf_path=pdf_file,
                db=db_session,
                document_settings=document_settings,
                ocr_settings=ocr_settings,
            )

    assert document_record.processing_status == "failed"


def test_ocr_processing_failure(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):

    native_result, _ = create_mock_results(
        str(document_record.id)
    )

    with patch(
        "app.services.document_processing_service.extract_pdf_text",
        return_value=native_result,
    ), patch(
        "app.services.document_processing_service.extract_pdf_with_ocr",
        side_effect=Exception("OCR failed"),
    ):

        with pytest.raises(DocumentProcessingError):

            process_document(
                document_record=document_record,
                pdf_path=pdf_file,
                db=db_session,
                document_settings=document_settings,
                ocr_settings=ocr_settings,
            )

    assert document_record.processing_status == "failed"


def test_invalid_document_uuid(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):

    document_record.id = "invalid-id"

    with pytest.raises(DocumentProcessingError):

        process_document(
            document_record=document_record,
            pdf_path=pdf_file,
            db=db_session,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )


def test_database_failure_when_marking_processing(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):

    db_session.commit.side_effect = RuntimeError(
        "Database unavailable"
    )

    with pytest.raises(DocumentProcessingDatabaseError):

        process_document(
            document_record=document_record,
            pdf_path=pdf_file,
            db=db_session,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )

    db_session.rollback.assert_called()


def test_processing_artifact_filename(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):

    native_result, ocr_result = create_mock_results(
        str(document_record.id)
    )

    with patch(
        "app.services.document_processing_service.extract_pdf_text",
        return_value=native_result,
    ), patch(
        "app.services.document_processing_service.extract_pdf_with_ocr",
        return_value=ocr_result,
    ):

        result = process_document(
            document_record=document_record,
            pdf_path=pdf_file,
            db=db_session,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )

    expected_name = (
        f"{document_record.id}_processed.json"
    )

    assert Path(result.artifact_path).name == expected_name

    def test_document_processing_status_transitions(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):
     native_result, ocr_result = create_mock_results(
        str(document_record.id)
    )

    recorded_statuses = []

    def record_commit():
        recorded_statuses.append(
            document_record.processing_status
        )

    db_session.commit.side_effect = record_commit

    with patch(
        "app.services.document_processing_service.extract_pdf_text",
        return_value=native_result,
    ), patch(
        "app.services.document_processing_service.extract_pdf_with_ocr",
        return_value=ocr_result,
    ):

        result = process_document(
            document_record=document_record,
            pdf_path=pdf_file,
            db=db_session,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )

    assert recorded_statuses == [
        "processing",
        "completed",
    ]

    assert result.processing_status == "completed"


def test_unified_artifact_contains_page_metadata(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):
    native_result, ocr_result = create_mock_results(
        str(document_record.id)
    )

    with patch(
        "app.services.document_processing_service.extract_pdf_text",
        return_value=native_result,
    ), patch(
        "app.services.document_processing_service.extract_pdf_with_ocr",
        return_value=ocr_result,
    ):

        result = process_document(
            document_record=document_record,
            pdf_path=pdf_file,
            db=db_session,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )

    artifact = json.loads(
        Path(result.artifact_path).read_text(
            encoding="utf-8"
        )
    )

    page = artifact["pages"][0]

    assert page["page_number"] == 1
    assert page["text"] == "Native text."
    assert page["extraction_method"] == "native"
    assert page["ocr_status"] == "not_required"
    assert page["word_count"] == 2


def test_artifact_failure_marks_document_failed(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):
    native_result, ocr_result = create_mock_results(
        str(document_record.id)
    )

    with patch(
        "app.services.document_processing_service.extract_pdf_text",
        return_value=native_result,
    ), patch(
        "app.services.document_processing_service.extract_pdf_with_ocr",
        return_value=ocr_result,
    ), patch(
        "app.services.document_processing_service._save_json_atomically",
        side_effect=OSError("Storage unavailable"),
    ):

        with pytest.raises(DocumentProcessingError):
            process_document(
                document_record=document_record,
                pdf_path=pdf_file,
                db=db_session,
                document_settings=document_settings,
                ocr_settings=ocr_settings,
            )

    assert document_record.processing_status == "failed"


def test_final_database_failure_removes_artifact(
    document_record,
    db_session,
    pdf_file,
    document_settings,
    ocr_settings,
):
    native_result, ocr_result = create_mock_results(
        str(document_record.id)
    )

    # First commit: processing.
    # Second commit: completed status fails.
    # Third commit: failed status is saved.
    db_session.commit.side_effect = [
        None,
        RuntimeError("Final database commit failed"),
        None,
    ]

    expected_artifact = (
        Path(document_settings.storage_root)
        / "processed"
        / f"{document_record.id}_processed.json"
    )

    with patch(
        "app.services.document_processing_service.extract_pdf_text",
        return_value=native_result,
    ), patch(
        "app.services.document_processing_service.extract_pdf_with_ocr",
        return_value=ocr_result,
    ):

        with pytest.raises(DocumentProcessingError):
            process_document(
                document_record=document_record,
                pdf_path=pdf_file,
                db=db_session,
                document_settings=document_settings,
                ocr_settings=ocr_settings,
            )

    assert document_record.processing_status == "failed"

    assert not expected_artifact.exists()

    assert db_session.rollback.called