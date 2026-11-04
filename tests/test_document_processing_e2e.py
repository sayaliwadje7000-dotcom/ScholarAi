import json
import os
import uuid

from pathlib import Path
from types import SimpleNamespace

import pytest
import pymupdf

from app.database.session import SessionLocal
from app.models.user import User
from app.models.document import Document

from app.core.document_config import DocumentSettings
from app.core.ocr_config import OCRSettings

from app.services.document_storage_service import (
    save_document,
    get_document_path,
)

from app.services.document_processing_service import (
    process_document,
)


pytestmark = pytest.mark.skipif(
    os.getenv("SCHOLARAI_RUN_DATABASE_INTEGRATION") != "1",
    reason="PostgreSQL integration tests are opt-in.",
)


@pytest.fixture
def document_settings(tmp_path):

    return DocumentSettings(
        storage_root=tmp_path / "storage",
        max_file_size_bytes=2 * 1024 * 1024,
        max_pages=10,
        allowed_extensions=(".pdf",),
        allowed_mime_types=("application/pdf",),
        create_storage_directories=True,
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
def db():

    session = SessionLocal()

    try:
        yield session

    finally:
        session.rollback()
        session.close()


@pytest.fixture
def registered_document(
    db,
    document_settings,
):

    user = User(
        full_name="Phase 7.20 E2E Test",
        email=f"phase720-{uuid.uuid4()}@example.test",
    )

    db.add(user)
    db.flush()

    pdf = pymupdf.open()

    page = pdf.new_page()

    page.insert_text(
        (72, 72),
        "ScholarAI end-to-end document processing test.",
    )

    pdf_content = pdf.tobytes()
    pdf.close()

    stored = save_document(
        content=pdf_content,
        original_filename="phase_720_test.pdf",
        content_type="application/pdf",
        settings=document_settings,
    )

    document = Document(
        user_id=user.id,
        original_filename=stored.original_filename,
        storage_key=stored.storage_key,
        mime_type=stored.mime_type,
        file_size_bytes=stored.file_size_bytes,
        checksum_sha256=stored.checksum_sha256,
        page_count=stored.page_count,
        processing_status="pending",
        processing_attempts=0,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    yield document

    document_id = document.id
    user_id = user.id
    storage_key = document.storage_key

    db.rollback()

    db.query(Document).filter(
        Document.id == document_id
    ).delete(synchronize_session=False)

    db.query(User).filter(
        User.id == user_id
    ).delete(synchronize_session=False)

    db.commit()

    stored_path = get_document_path(
        storage_key,
        document_settings,
    )

    stored_path.unlink(missing_ok=True)


def configure_processing_stage_mocks(
    monkeypatch,
    document_settings,
):

    page = SimpleNamespace(
        page_number=1,
        text="ScholarAI end-to-end document processing test.",
        extraction_method="native",
        ocr_status="not_required",
        character_count=48,
        word_count=6,
        average_confidence=None,
        low_confidence=False,
        warnings=[],
    )

    native_result = SimpleNamespace(
        document_id="",
        page_count=1,
        pages=[page],
        total_characters=48,
        total_words=6,
    )

    ocr_result = SimpleNamespace(
        document_id="",
        page_count=1,
        pages=[page],
        total_characters=48,
        total_words=6,
        pages_with_text=1,
        extraction_method="native",
        quality_status="good",
        ocr_pages=0,
        failed_pages=0,
        average_ocr_confidence=None,
        warnings=[],
    )

    cleaning_page = SimpleNamespace(
        page_number=1,
        text="ScholarAI end-to-end document processing test.",
        character_count=48,
        word_count=6,
    )

    cleaning_result = SimpleNamespace(
        pages=[cleaning_page],
        warnings=[],
    )

    chunking_result = SimpleNamespace(
        document_id="",
        chunk_count=1,
        chunks=[
            {
                "chunk_index": 0,
                "page_number": 1,
                "text": "ScholarAI end-to-end document processing test.",
            }
        ],
    )

    processed_directory = (
        Path(document_settings.storage_root)
        / "processed"
    )

    processed_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    def save_test_artifact(filename, payload):

        path = processed_directory / filename

        path.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

        return path

    monkeypatch.setattr(
        "app.services.document_processing_service.extract_pdf_text",
        lambda **kwargs: native_result,
    )

    monkeypatch.setattr(
        "app.services.document_processing_service.extract_pdf_with_ocr",
        lambda **kwargs: ocr_result,
    )

    monkeypatch.setattr(
        "app.services.document_processing_service.clean_document_text",
        lambda **kwargs: cleaning_result,
    )

    monkeypatch.setattr(
        "app.services.document_processing_service.save_cleaned_text_artifact",
        lambda **kwargs: save_test_artifact(
            f"{kwargs['result'].pages[0].page_number}_cleaned.json",
            {"text": kwargs["result"].pages[0].text},
        ),
    )

    monkeypatch.setattr(
        "app.services.document_processing_service.process_document_structure",
        lambda **kwargs: (
            {"headings": [], "paragraphs": 1},
            save_test_artifact(
                "structure.json",
                {"paragraphs": 1},
            ),
        ),
    )

    monkeypatch.setattr(
        "app.services.document_processing_service.chunk_document_pages",
        lambda **kwargs: chunking_result,
    )

    monkeypatch.setattr(
        "app.services.document_processing_service.save_chunking_artifact",
        lambda **kwargs: save_test_artifact(
            "chunks.json",
            {"chunk_count": 1},
        ),
    )


def test_complete_document_processing_lifecycle(
    db,
    registered_document,
    document_settings,
    ocr_settings,
    monkeypatch,
):

    configure_processing_stage_mocks(
        monkeypatch,
        document_settings,
    )

    pdf_path = get_document_path(
        registered_document.storage_key,
        document_settings,
    )

    result = process_document(
        document_record=registered_document,
        pdf_path=pdf_path,
        db=db,
        document_settings=document_settings,
        ocr_settings=ocr_settings,
    )

    db.expire_all()

    persisted = db.get(
        Document,
        registered_document.id,
    )

    assert result.processing_status == "completed"

    assert persisted.processing_status == "completed"

    assert persisted.processing_attempts == 1

    assert persisted.processing_started_at is not None

    assert persisted.processing_completed_at is not None

    assert persisted.processing_error is None

    assert persisted.page_count == 1

    artifact_path = Path(result.artifact_path)

    assert artifact_path.is_file()

    artifact = json.loads(
        artifact_path.read_text(encoding="utf-8")
    )

    assert artifact["processing_status"] == "completed"

    assert artifact["document_id"] == str(persisted.id)

    assert artifact["page_count"] == 1

    assert artifact["chunking"]["chunk_count"] == 1

    assert Path(
        artifact["chunking_artifact_path"]
    ).is_file()


def test_corrupted_pdf_persists_failure_status(
    db,
    registered_document,
    document_settings,
    ocr_settings,
):

    pdf_path = get_document_path(
        registered_document.storage_key,
        document_settings,
    )

    pdf_path.write_bytes(
        b"CORRUPTED PDF CONTENT"
    )

    with pytest.raises(Exception):

        process_document(
            document_record=registered_document,
            pdf_path=pdf_path,
            db=db,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )

    db.expire_all()

    persisted = db.get(
        Document,
        registered_document.id,
    )

    assert persisted.processing_status == "failed"

    assert persisted.processing_attempts == 1

    assert persisted.processing_completed_at is not None

    assert persisted.processing_error is not None

    assert "integrity" in persisted.processing_error.lower() \
        or "size" in persisted.processing_error.lower()