import hashlib
import hmac
import logging
import os
import re
import unicodedata
import uuid

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
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


def verify_document_checksum(
    storage_key: str,
    expected_checksum: str,
    settings: DocumentSettings = document_settings,
) -> bool:
    """
    Verify the SHA-256 checksum of a stored document.

    Reads the document in chunks to avoid loading the entire file
    into memory.

    Returns True when the stored document matches the expected checksum.

    Raises:
        DocumentValidationError: If the expected checksum is invalid.
        DocumentStorageError: If the document cannot be accessed.
        DocumentIntegrityError: If the checksum does not match.
    """

    if (
        not isinstance(expected_checksum, str)
        or not re.fullmatch(r"[a-fA-F0-9]{64}", expected_checksum)
    ):
        raise DocumentValidationError(
            "A valid SHA-256 checksum is required."
        )

    path = get_document_path(
        storage_key,
        settings,
    )

    digest = hashlib.sha256()

    try:
        with path.open("rb") as file:
            while True:
                chunk = file.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)

    except OSError as exc:
        raise DocumentStorageError(
            "Unable to read the stored document for integrity verification."
        ) from exc

    actual_checksum = digest.hexdigest()

    if not hmac.compare_digest(
        actual_checksum,
        expected_checksum.lower(),
    ):
        raise DocumentIntegrityError(
            "Stored document integrity verification failed."
        )

    return True


# ============================================================
# STORAGE PATH RESOLUTION
# ============================================================

def resolve_storage_path(
    storage_key: str,
    settings: DocumentSettings = document_settings,
) -> Path:
    """
    Resolve a storage key safely.

    Reject:
    - Absolute paths
    - Windows drive paths
    - POSIX and Windows traversal
    - Null bytes
    - Paths escaping the configured storage root
    - Symlink resolutions outside the storage root

    Storage keys use POSIX-style separators.
    """

    if not isinstance(storage_key, str) or not storage_key:
        raise DocumentStorageError(
            "A valid storage key is required."
        )

    if "\x00" in storage_key:
        raise DocumentStorageError(
            "Invalid storage key."
        )

    normalized_key = storage_key.replace("\\", "/")

    windows_path = PureWindowsPath(normalized_key)
    posix_path = PurePosixPath(normalized_key)

    if (
        Path(normalized_key).is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or posix_path.is_absolute()
        or ".." in posix_path.parts
        or ".." in windows_path.parts
    ):
        raise DocumentStorageError(
            "Unsafe storage paths are not allowed."
        )

    if not posix_path.parts:
        raise DocumentStorageError(
            "A valid storage key is required."
        )

    try:
        root = settings.storage_root.resolve()

        destination = root.joinpath(
            *posix_path.parts
        ).resolve()

        if not destination.is_relative_to(root):
            raise DocumentStorageError(
                "The storage path escapes the document storage root."
            )

        return destination

    except DocumentStorageError:
        raise

    except (OSError, RuntimeError, ValueError) as exc:
        raise DocumentStorageError(
            "Unable to safely resolve the document storage path."
        ) from exc

# ============================================================
# ATOMIC FILE WRITING
# ============================================================

def _write_file_atomically(
    destination: Path,
    content: bytes,
) -> None:
    """
    Write content to a unique temporary file.

    Publish the completed file using an atomic hard-link
    operation so an existing destination cannot be overwritten.

    The temporary file and destination must be on the same
    filesystem.
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

        # Atomic publication without replacing an existing file.
        # os.link fails if destination already exists.
        os.link(
            temporary_path,
            destination,
        )

    except FileExistsError as exc:
        raise DocumentStorageWriteError(
            "The destination document already exists."
        ) from exc

    except OSError as exc:
        raise DocumentStorageWriteError(
            "Unable to store the uploaded document safely."
        ) from exc

    except Exception as exc:
        raise DocumentStorageWriteError(
            "Unexpected error while storing the uploaded document."
        ) from exc

    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                logger.exception(
                    "Unable to close temporary storage file descriptor."
                )

        try:
            temporary_path.unlink(
                missing_ok=True
            )
        except OSError:
            logger.exception(
                "Unable to remove temporary storage file: %s",
                temporary_path,
            )
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