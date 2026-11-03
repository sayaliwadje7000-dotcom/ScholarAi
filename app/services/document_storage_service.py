import hashlib
import logging
import os
import re
import unicodedata
import uuid

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

import pymupdf as fitz
from app.core.document_config import (
    DocumentSettings,
    document_settings,
    get_storage_directories,
)


logger = logging.getLogger(__name__)


# ============================================================
# EXCEPTIONS
# ============================================================

class DocumentStorageError(Exception):
    """Base exception for document storage operations."""


class DocumentValidationError(DocumentStorageError):
    """Raised when an uploaded document fails validation."""


class DocumentSizeError(DocumentValidationError):
    """Raised when an uploaded document exceeds the size limit."""


class DocumentIntegrityError(DocumentValidationError):
    """Raised when a PDF is malformed or invalid."""


class DocumentStorageWriteError(DocumentStorageError):
    """Raised when a document cannot be safely stored."""


# ============================================================
# RESULT MODEL
# ============================================================

@dataclass(frozen=True)
class StoredDocument:
    """
    Metadata returned after successfully storing a PDF.
    """

    document_id: uuid.UUID

    storage_key: str

    original_filename: str

    mime_type: str

    file_size_bytes: int

    checksum_sha256: str

    page_count: int


# ============================================================
# FILENAME SANITIZATION
# ============================================================

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a user-provided filename.

    The filename is retained only as metadata.
    It is never used as a storage path.
    """

    if not isinstance(filename, str):
        raise DocumentValidationError(
            "A valid filename is required."
        )

    filename = unicodedata.normalize(
        "NFKC",
        filename,
    )

    # Handle both Windows and POSIX path separators.
    filename = filename.replace("\\", "/")

    filename = filename.split("/")[-1]

    filename = re.sub(
        r"[\x00-\x1f\x7f]",
        "",
        filename,
    )

    filename = re.sub(
        r"[^a-zA-Z0-9._ -]",
        "_",
        filename,
    )

    filename = filename.strip(" .")

    if not filename:
        raise DocumentValidationError(
            "The supplied filename is invalid."
        )

    if not filename.lower().endswith(".pdf"):
        raise DocumentValidationError(
            "Only PDF filenames are supported."
        )

    # Retain the extension while limiting the filename.
    stem = filename[:-4].strip(" .")

    if not stem:
        stem = "document"

    return f"{stem[:250]}.pdf"


# ============================================================
# FILE SIZE VALIDATION
# ============================================================

def validate_file_size(
    content: bytes,
    settings: DocumentSettings = document_settings,
) -> None:
    """
    Validate that the uploaded content is non-empty
    and within the configured maximum size.
    """

    if not isinstance(content, bytes):
        raise DocumentValidationError(
            "Document content must be bytes."
        )

    if len(content) == 0:
        raise DocumentValidationError(
            "The uploaded PDF is empty."
        )

    if len(content) > settings.max_file_size_bytes:
        raise DocumentSizeError(
            "The uploaded document exceeds the "
            "maximum permitted file size."
        )


# ============================================================
# MIME TYPE VALIDATION
# ============================================================

def validate_mime_type(
    content_type: str | None,
    settings: DocumentSettings = document_settings,
) -> None:
    """
    Validate the declared MIME type.

    application/octet-stream is accepted because some clients
    send generic binary content types for uploaded PDFs.

    The actual file format is independently validated.
    """

    if content_type is None:
        return

    normalized = content_type.split(";")[0].strip().lower()

    allowed_types = {
        *settings.allowed_mime_types,
        "application/octet-stream",
    }

    if normalized not in allowed_types:
        raise DocumentValidationError(
            "Unsupported content type. Upload a PDF document."
        )


# ============================================================
# PDF SIGNATURE VALIDATION
# ============================================================

def validate_pdf_signature(content: bytes) -> None:
    """
    Check for a PDF header near the beginning of the file.

    PDF parsing is still required afterward.
    """

    header_region = content[:1024]

    if b"%PDF-" not in header_region:
        raise DocumentIntegrityError(
            "The uploaded file does not contain a valid PDF header."
        )


# ============================================================
# PDF STRUCTURE VALIDATION
# ============================================================

def validate_pdf_structure(
    content: bytes,
    settings: DocumentSettings = document_settings,
) -> int:
    """
    Parse the PDF and validate its structural properties.

    Returns the number of pages.
    """

    try:
        with fitz.open(
            stream=content,
            filetype="pdf",
        ) as pdf:

            if pdf.is_encrypted:
                raise DocumentIntegrityError(
                    "Password-protected PDFs are not supported."
                )

            page_count = pdf.page_count

            if page_count <= 0:
                raise DocumentIntegrityError(
                    "The PDF does not contain any pages."
                )

            if page_count > settings.max_pages:
                raise DocumentValidationError(
                    f"The PDF exceeds the maximum allowed "
                    f"page count of {settings.max_pages}."
                )

            return page_count

    except DocumentStorageError:
        raise

    except Exception as exc:
        logger.warning(
            "PDF structural validation failed: %s",
            exc,
        )

        raise DocumentIntegrityError(
            "The uploaded file is not a readable PDF."
        ) from exc


# ============================================================
# SHA-256 CHECKSUM
# ============================================================

def calculate_sha256(content: bytes) -> str:
    """
    Calculate the SHA-256 checksum of document content.
    """

    return hashlib.sha256(content).hexdigest()


# ============================================================
# STORAGE PATH RESOLUTION
# ============================================================

def resolve_storage_path(
    storage_key: str,
    settings: DocumentSettings = document_settings,
) -> Path:
    """
    Resolve a storage key safely.

    Reject absolute paths, traversal and paths escaping
    the configured storage root.
    """

    if not isinstance(storage_key, str) or not storage_key:
        raise DocumentStorageError(
            "A valid storage key is required."
        )

    if "\x00" in storage_key:
        raise DocumentStorageError(
            "Invalid storage key."
        )

    # Reject Windows absolute paths even on other platforms.
    windows_path = PureWindowsPath(storage_key)

    if (
        Path(storage_key).is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
    ):
        raise DocumentStorageError(
            "Absolute storage paths are not allowed."
        )

    root = settings.storage_root.resolve()

    destination = (
        root / storage_key
    ).resolve()

    if not destination.is_relative_to(root):
        raise DocumentStorageError(
            "The storage path escapes the document storage root."
        )

    return destination


# ============================================================
# ATOMIC FILE WRITING
# ============================================================

def _write_file_atomically(
    destination: Path,
    content: bytes,
) -> None:
    """
    Write content to a unique temporary file and atomically
    move it to its final destination.

    Temporary files are created in the same directory
    to keep the replacement on the same filesystem.
    """

    temporary_path = destination.with_name(
        f".{destination.name}.{uuid.uuid4().hex}.part"
    )

    file_descriptor = None

    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL

        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY

        file_descriptor = os.open(
            temporary_path,
            flags,
            0o600,
        )

        with os.fdopen(
            file_descriptor,
            "wb",
        ) as file:

            file_descriptor = None

            file.write(content)

            file.flush()

            os.fsync(file.fileno())

        # Generated UUID filenames make collisions extremely
        # unlikely. The destination must not already exist.
        if destination.exists():
            raise FileExistsError(
                "The generated document path already exists."
            )

        os.replace(
            temporary_path,
            destination,
        )

    except Exception as exc:

        if file_descriptor is not None:
            os.close(file_descriptor)

        temporary_path.unlink(
            missing_ok=True
        )

        raise DocumentStorageWriteError(
            "Unable to store the uploaded document."
        ) from exc


# ============================================================
# DOCUMENT STORAGE
# ============================================================

def save_document(
    content: bytes,
    original_filename: str,
    content_type: str | None = None,
    settings: DocumentSettings = document_settings,
) -> StoredDocument:
    """
    Validate and store an uploaded PDF.

    Processing order:

    1. Validate file size.
    2. Validate filename.
    3. Validate declared MIME type.
    4. Validate PDF signature.
    5. Parse and validate PDF structure.
    6. Calculate SHA-256.
    7. Generate a storage identifier.
    8. Write the file atomically.

    Returns metadata about the stored document.
    """

    validate_file_size(
        content,
        settings,
    )

    safe_filename = sanitize_filename(
        original_filename
    )

    validate_mime_type(
        content_type,
        settings,
    )

    validate_pdf_signature(
        content
    )

    page_count = validate_pdf_structure(
        content,
        settings,
    )

    checksum = calculate_sha256(
        content
    )

    document_id = uuid.uuid4()

    storage_key = (
        f"documents/{document_id}.pdf"
    )

    directories = get_storage_directories(
        settings
    )

    documents_directory = directories["documents"]

    try:
        documents_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = resolve_storage_path(
            storage_key,
            settings,
        )

        # Re-check after directory creation to reject
        # an unexpected symlink/path change.
        if not destination.parent.is_dir():
            raise DocumentStorageWriteError(
                "Document storage directory is unavailable."
            )

        _write_file_atomically(
            destination,
            content,
        )

    except DocumentStorageError:
        raise

    except OSError as exc:
        raise DocumentStorageWriteError(
            "Unable to initialize document storage."
        ) from exc

    return StoredDocument(
        document_id=document_id,
        storage_key=storage_key,
        original_filename=safe_filename,
        mime_type="application/pdf",
        file_size_bytes=len(content),
        checksum_sha256=checksum,
        page_count=page_count,
    )


# ============================================================
# DOCUMENT RETRIEVAL
# ============================================================

def get_document_path(
    storage_key: str,
    settings: DocumentSettings = document_settings,
) -> Path:
    """
    Return the safe physical path of a stored document.
    """

    path = resolve_storage_path(
        storage_key,
        settings,
    )

    if not path.is_file():
        raise DocumentStorageError(
            "The requested document does not exist."
        )

    return path


# ============================================================
# DOCUMENT DELETION
# ============================================================

def delete_document(
    storage_key: str,
    settings: DocumentSettings = document_settings,
) -> None:
    """
    Delete a document using its storage key.

    Missing files are treated as already deleted.
    """

    path = resolve_storage_path(
        storage_key,
        settings,
    )

    try:
        path.unlink(
            missing_ok=True
        )

    except OSError as exc:
        raise DocumentStorageWriteError(
            "Unable to delete the stored document."
        ) from exc