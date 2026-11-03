import hashlib
import uuid
import pytest
import pymupdf as fitz
from pathlib import Path

from app.core.document_config import DocumentSettings

from app.services.document_storage_service import (
    DocumentStorageError,
    DocumentValidationError,
    DocumentSizeError,
    DocumentIntegrityError,
    calculate_sha256,
    delete_document,
    get_document_path,
    resolve_storage_path,
    sanitize_filename,
    save_document,
    validate_file_size,
    validate_mime_type,
    validate_pdf_signature,
    validate_pdf_structure,
)


# ============================================================
# TEST FIXTURES
# ============================================================

@pytest.fixture
def document_settings_fixture(tmp_path):

    return DocumentSettings(
        storage_root=tmp_path / "storage",

        max_file_size_bytes=1024 * 1024,

        max_pages=5,

        allowed_extensions=(".pdf",),

        allowed_mime_types=("application/pdf",),

        create_storage_directories=True,
    )


@pytest.fixture
def valid_pdf():

    document = fitz.open()

    page = document.new_page()

    page.insert_text(
        (72, 72),
        "ScholarAI document storage testing.",
    )

    content = document.tobytes()

    document.close()

    return content


# ============================================================
# FILENAME TESTS
# ============================================================

def test_sanitize_normal_filename():

    result = sanitize_filename(
        "lecture_notes.pdf"
    )

    assert result == "lecture_notes.pdf"


def test_sanitize_windows_path():

    result = sanitize_filename(
        r"..\..\private\lecture.pdf"
    )

    assert result == "lecture.pdf"


def test_sanitize_posix_path():

    result = sanitize_filename(
        "../../private/lecture.pdf"
    )

    assert result == "lecture.pdf"


def test_sanitize_invalid_extension():

    with pytest.raises(DocumentValidationError):

        sanitize_filename(
            "lecture.docx"
        )


def test_sanitize_empty_filename():

    with pytest.raises(DocumentValidationError):

        sanitize_filename(
            "../../"
        )


def test_sanitize_filename_length():

    result = sanitize_filename(
        ("a" * 300) + ".pdf"
    )

    assert len(result) <= 254

    assert result.endswith(".pdf")


# ============================================================
# FILE SIZE TESTS
# ============================================================

def test_reject_empty_file(
    document_settings_fixture,
):

    with pytest.raises(DocumentValidationError):

        validate_file_size(
            b"",
            document_settings_fixture,
        )


def test_reject_oversized_file(
    document_settings_fixture,
):

    content = b"A" * (
        document_settings_fixture.max_file_size_bytes + 1
    )

    with pytest.raises(DocumentSizeError):

        validate_file_size(
            content,
            document_settings_fixture,
        )


def test_accept_file_within_limit(
    document_settings_fixture,
):

    content = b"A" * 100

    validate_file_size(
        content,
        document_settings_fixture,
    )


# ============================================================
# MIME TYPE TESTS
# ============================================================

def test_accept_pdf_mime_type(
    document_settings_fixture,
):

    validate_mime_type(
        "application/pdf",
        document_settings_fixture,
    )


def test_accept_generic_binary_mime_type(
    document_settings_fixture,
):

    validate_mime_type(
        "application/octet-stream",
        document_settings_fixture,
    )


def test_accept_missing_mime_type(
    document_settings_fixture,
):

    validate_mime_type(
        None,
        document_settings_fixture,
    )


def test_reject_unsupported_mime_type(
    document_settings_fixture,
):

    with pytest.raises(DocumentValidationError):

        validate_mime_type(
            "image/png",
            document_settings_fixture,
        )


# ============================================================
# PDF SIGNATURE TESTS
# ============================================================

def test_accept_pdf_signature(valid_pdf):

    validate_pdf_signature(
        valid_pdf
    )


def test_reject_invalid_pdf_signature():

    with pytest.raises(DocumentIntegrityError):

        validate_pdf_signature(
            b"THIS IS NOT A PDF"
        )


# ============================================================
# PDF STRUCTURE TESTS
# ============================================================

def test_validate_valid_pdf(
    valid_pdf,
    document_settings_fixture,
):

    page_count = validate_pdf_structure(
        valid_pdf,
        document_settings_fixture,
    )

    assert page_count == 1


def test_reject_invalid_pdf_structure(
    document_settings_fixture,
):

    content = b"%PDF-1.7\ninvalid content"

    with pytest.raises(DocumentIntegrityError):

        validate_pdf_structure(
            content,
            document_settings_fixture,
        )


def test_reject_zero_page_pdf(
    document_settings_fixture,
):
    # Create a valid PDF containing one page.
    document = fitz.open()

    document.new_page()

    content = document.tobytes()

    document.close()

    # Modify the test input to represent a PDF
    # that cannot be parsed as a valid document.
    invalid_content = content[:100]

    with pytest.raises(DocumentIntegrityError):

        validate_pdf_structure(
            invalid_content,
            document_settings_fixture,
        )


def test_reject_excessive_page_count(
    document_settings_fixture,
):

    document = fitz.open()

    for _ in range(6):
        document.new_page()

    content = document.tobytes()

    document.close()

    with pytest.raises(DocumentValidationError):

        validate_pdf_structure(
            content,
            document_settings_fixture,
        )


def test_reject_encrypted_pdf(
    document_settings_fixture,
):

    document = fitz.open()

    document.new_page()

    content = document.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-password",
        user_pw="user-password",
    )

    document.close()

    with pytest.raises(DocumentIntegrityError):

        validate_pdf_structure(
            content,
            document_settings_fixture,
        )


# ============================================================
# CHECKSUM TESTS
# ============================================================

def test_checksum_matches_hashlib():

    content = b"ScholarAI"

    assert calculate_sha256(content) == (
        hashlib.sha256(content).hexdigest()
    )


def test_checksum_is_64_characters():

    result = calculate_sha256(
        b"ScholarAI"
    )

    assert len(result) == 64


# ============================================================
# PATH SECURITY TESTS
# ============================================================

@pytest.mark.parametrize(
    "storage_key",
    [
        "../outside.pdf",
        "../../secret.pdf",
        "C:\\private\\document.pdf",
        "/etc/passwd",
        "",
    ],
)
def test_reject_unsafe_storage_keys(
    storage_key,
    document_settings_fixture,
):

    with pytest.raises(DocumentStorageError):

        resolve_storage_path(
            storage_key,
            document_settings_fixture,
        )


def test_resolve_valid_storage_key(
    document_settings_fixture,
):

    result = resolve_storage_path(
        "documents/sample.pdf",
        document_settings_fixture,
    )

    assert result == (
        document_settings_fixture.storage_root
        / "documents"
        / "sample.pdf"
    ).resolve()


# ============================================================
# STORAGE TESTS
# ============================================================

def test_save_document(
    valid_pdf,
    document_settings_fixture,
):

    result = save_document(
        content=valid_pdf,
        original_filename="lecture.pdf",
        content_type="application/pdf",
        settings=document_settings_fixture,
    )

    assert isinstance(
        result.document_id,
        uuid.UUID,
    )

    assert result.original_filename == "lecture.pdf"

    assert result.mime_type == "application/pdf"

    assert result.file_size_bytes == len(valid_pdf)

    assert result.page_count == 1

    stored_path = get_document_path(
        result.storage_key,
        document_settings_fixture,
    )

    assert stored_path.is_file()

    assert stored_path.read_bytes() == valid_pdf


def test_saved_checksum_matches_content(
    valid_pdf,
    document_settings_fixture,
):

    result = save_document(
        valid_pdf,
        "notes.pdf",
        settings=document_settings_fixture,
    )

    assert result.checksum_sha256 == (
        hashlib.sha256(valid_pdf).hexdigest()
    )


def test_generated_storage_names_are_unique(
    valid_pdf,
    document_settings_fixture,
):

    first = save_document(
        valid_pdf,
        "notes.pdf",
        settings=document_settings_fixture,
    )

    second = save_document(
        valid_pdf,
        "notes.pdf",
        settings=document_settings_fixture,
    )

    assert first.storage_key != second.storage_key


def test_reject_invalid_upload_without_storage(
    document_settings_fixture,
):

    with pytest.raises(DocumentIntegrityError):

        save_document(
            b"NOT A PDF",
            "invalid.pdf",
            settings=document_settings_fixture,
        )

    documents_directory = (
        document_settings_fixture.storage_root
        / "documents"
    )

    assert not documents_directory.exists()


def test_delete_document(
    valid_pdf,
    document_settings_fixture,
):

    result = save_document(
        valid_pdf,
        "notes.pdf",
        settings=document_settings_fixture,
    )

    path = get_document_path(
        result.storage_key,
        document_settings_fixture,
    )

    assert path.exists()

    delete_document(
        result.storage_key,
        document_settings_fixture,
    )

    assert not path.exists()


def test_delete_missing_document(
    document_settings_fixture,
):

    delete_document(
        "documents/nonexistent.pdf",
        document_settings_fixture,
    )