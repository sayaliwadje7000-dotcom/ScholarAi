from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.document_config import DocumentSettings

from app.services.document_processing_service import (
    DocumentProcessingError,
    _validate_stored_document,
)


@pytest.fixture
def document_settings(tmp_path):
    return DocumentSettings(
        storage_root=tmp_path,
        max_file_size_bytes=20 * 1024 * 1024,
        max_pages=100,
        allowed_extensions=(".pdf",),
        allowed_mime_types=("application/pdf",),
        create_storage_directories=True,
    )


@pytest.fixture
def stored_document(tmp_path):
    document_directory = tmp_path / "documents"
    document_directory.mkdir()

    pdf_path = document_directory / "sample.pdf"
    pdf_content = b"%PDF-1.7 test content"

    pdf_path.write_bytes(pdf_content)

    document = SimpleNamespace(
        storage_key="documents/sample.pdf",
        checksum_sha256="a" * 64,
        file_size_bytes=len(pdf_content),
    )

    return document, pdf_path


def test_rejects_missing_storage_metadata(
    document_settings,
    tmp_path,
):
    document = SimpleNamespace(
        storage_key=None,
        checksum_sha256=None,
        file_size_bytes=100,
    )

    with pytest.raises(DocumentProcessingError):
        _validate_stored_document(
            document_record=document,
            pdf_path=tmp_path / "sample.pdf",
            document_settings=document_settings,
        )


def test_rejects_different_file_path(
    document_settings,
    stored_document,
    tmp_path,
):
    document, _ = stored_document

    different_path = tmp_path / "different.pdf"
    different_path.write_bytes(b"%PDF-1.7 different")

    with pytest.raises(DocumentProcessingError):
        _validate_stored_document(
            document_record=document,
            pdf_path=different_path,
            document_settings=document_settings,
        )


def test_rejects_file_size_mismatch(
    document_settings,
    stored_document,
):
    document, pdf_path = stored_document
    document.file_size_bytes += 1

    with pytest.raises(DocumentProcessingError):
        _validate_stored_document(
            document_record=document,
            pdf_path=pdf_path,
            document_settings=document_settings,
        )


def test_rejects_checksum_mismatch(
    document_settings,
    stored_document,
):
    document, pdf_path = stored_document

    with patch(
        "app.services.document_processing_service.verify_document_checksum",
        side_effect=Exception("checksum mismatch"),
    ):
        with pytest.raises(DocumentProcessingError):
            _validate_stored_document(
                document_record=document,
                pdf_path=pdf_path,
                document_settings=document_settings,
            )


def test_accepts_valid_registered_document(
    document_settings,
    stored_document,
):
    document, pdf_path = stored_document

    with patch(
        "app.services.document_processing_service.verify_document_checksum",
        return_value=True,
    ):
        result = _validate_stored_document(
            document_record=document,
            pdf_path=pdf_path,
            document_settings=document_settings,
        )

    assert result == pdf_path.resolve()