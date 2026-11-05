import json
import logging
import os
import tempfile

from copy import copy
from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.document_config import DocumentSettings
from app.core.ocr_config import OCRSettings
from app.core.text_cleaning_config import TextCleaningSettings
from app.core.chunking_config import ChunkingSettings

from app.services.pdf_extraction_service import (
    extract_pdf_text,
    PDFExtractionError,
)

from app.services.ocr_service import (
    extract_pdf_with_ocr,
    OCRProcessingError,
)

from app.services.document_structure_service import (
    process_document_structure,
)

from app.services.text_cleaning_service import (
    clean_document_text,
    save_cleaned_text_artifact,
)

from app.services.document_chunking_service import (
    chunk_document_pages,
    save_chunking_artifact,
)

# Phase 8.10: Document chunk persistence and embedding integration
from app.services.document_indexing_service import (
    index_document_chunks,
)

from app.services.document_status_service import (
    claim_document_for_processing,
    DocumentAlreadyClaimedError,
)

from app.services.document_storage_service import (
    get_document_path,
    verify_document_checksum,
)

from app.services.document_observability_service import (
    document_observability,
    observe_processing_stage,
)

logger = logging.getLogger(__name__)


# ==========================================================
# EXCEPTIONS
# ==========================================================

class DocumentProcessingError(Exception):
    """Base exception for document processing."""


class DocumentProcessingStorageError(DocumentProcessingError):
    """Raised when a processing artifact cannot be saved."""


class DocumentProcessingDatabaseError(DocumentProcessingError):
    """Raised when document status cannot be updated."""


class DocumentProcessingAlreadyClaimedError(DocumentProcessingError):
    """Raised when another worker has already claimed this document."""


# ==========================================================
# RESULT MODEL
# ==========================================================

@dataclass(frozen=True)
class DocumentProcessingResult:

    document_id: str
    processing_status: str
    processing_started_at: str
    processing_completed_at: str
    processing_duration_seconds: float
    page_count: int
    total_characters: int
    total_words: int
    pages_with_text: int
    extraction_method: str
    quality_status: str
    artifact_path: str
    warnings: list[str]


# ==========================================================
# GENERAL HELPERS
# ==========================================================

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat()


def _replace_object(instance, **updates):
    """
    Return an updated copy of a dataclass or ordinary object.

    Supports SimpleNamespace objects used in tests.
    """

    try:
        return replace(instance, **updates)

    except TypeError:
        updated_instance = copy(instance)

        for key, value in updates.items():
            setattr(updated_instance, key, value)

        return updated_instance


def _to_dict(value):
    """
    Recursively convert objects into JSON-compatible values.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (UUID, Path)):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if is_dataclass(value) and not isinstance(value, type):
        return {
            key: _to_dict(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, dict):
        return {
            str(key): _to_dict(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            _to_dict(item)
            for item in value
        ]

    if hasattr(value, "__dict__"):
        return {
            key: _to_dict(item)
            for key, item in vars(value).items()
        }

    raise TypeError(
        f"Cannot serialize object of type {type(value).__name__}."
    )


# ==========================================================
# PHASE 7.15 - CONFIGURATION VALIDATION
# ==========================================================

def _validate_processing_configuration(
    *,
    document_settings: DocumentSettings,
    ocr_settings: OCRSettings,
    cleaning_settings: TextCleaningSettings,
    chunking_settings: ChunkingSettings,
) -> None:
    """Validate all processing configuration objects."""

    if not isinstance(document_settings, DocumentSettings):
        raise DocumentProcessingError(
            "Invalid document processing configuration."
        )

    if not isinstance(ocr_settings, OCRSettings):
        raise DocumentProcessingError(
            "Invalid OCR configuration."
        )

    if not isinstance(cleaning_settings, TextCleaningSettings):
        raise DocumentProcessingError(
            "Invalid text-cleaning configuration."
        )

    if not isinstance(chunking_settings, ChunkingSettings):
        raise DocumentProcessingError(
            "Invalid chunking configuration."
        )


# ==========================================================
# PHASE 7.15 - STORED DOCUMENT INTEGRITY VALIDATION
# ==========================================================

def _validate_stored_document(
    *,
    document_record,
    pdf_path: Path,
    document_settings: DocumentSettings,
) -> Path:
    """
    Validate the PDF supplied for processing.

    Database-backed document records must have:
    - storage_key
    - checksum_sha256
    - file_size_bytes

    Legacy lightweight test doubles without these attributes
    can still exercise the processing pipeline using an
    existing PDF path.
    """

    pdf_path = Path(pdf_path)

    metadata_fields = (
        "storage_key",
        "checksum_sha256",
        "file_size_bytes",
    )

    metadata_attributes_present = [
        hasattr(document_record, field)
        for field in metadata_fields
    ]

    # Compatibility for legacy lightweight test doubles.
    # Actual SQLAlchemy Document models expose all three fields.
    if not any(metadata_attributes_present):

        if not pdf_path.is_file():
            raise DocumentProcessingError(
                "Stored PDF file does not exist."
            )

        logger.warning(
            "Document %s has no storage metadata attributes. "
            "Using legacy processing compatibility mode.",
            getattr(document_record, "id", "unknown"),
        )

        return pdf_path.resolve()

    # Partially populated metadata is never accepted.
    if not all(metadata_attributes_present):
        raise DocumentProcessingError(
            "Document storage metadata is incomplete."
        )

    storage_key = document_record.storage_key
    expected_checksum = document_record.checksum_sha256
    expected_size = document_record.file_size_bytes

    if (
        not isinstance(storage_key, str)
        or not storage_key.strip()
    ):
        raise DocumentProcessingError(
            "Document storage key is invalid."
        )

    if (
        not isinstance(expected_checksum, str)
        or len(expected_checksum) != 64
    ):
        raise DocumentProcessingError(
            "Document checksum metadata is invalid."
        )

    if (
        not isinstance(expected_size, int)
        or isinstance(expected_size, bool)
        or expected_size <= 0
    ):
        raise DocumentProcessingError(
            "Document size metadata is invalid."
        )

    try:

        registered_path = get_document_path(
            storage_key,
            document_settings,
        )

        registered_path = registered_path.resolve()
        supplied_path = pdf_path.resolve()

    except Exception as exc:

        raise DocumentProcessingError(
            "Unable to resolve the registered document."
        ) from exc

    # Verify that the supplied path belongs to this document.
    if supplied_path != registered_path:
        raise DocumentProcessingError(
            "The supplied file does not match the registered document."
        )

    if not registered_path.is_file():
        raise DocumentProcessingError(
            "The registered document file does not exist."
        )

    # Verify stored file size.
    try:
        actual_size = registered_path.stat().st_size

    except OSError as exc:
        raise DocumentProcessingError(
            "Unable to inspect the registered document."
        ) from exc

    if actual_size != expected_size:
        raise DocumentProcessingError(
            "Stored document size verification failed."
        )

    # Verify SHA-256 checksum.
    try:

        verify_document_checksum(
            storage_key=storage_key,
            expected_checksum=expected_checksum,
            settings=document_settings,
        )

    except Exception as exc:

        raise DocumentProcessingError(
            "Stored document integrity verification failed."
        ) from exc

    return registered_path


# ==========================================================
# ATOMIC JSON STORAGE
# ==========================================================

def _save_json_atomically(
    payload: dict,
    destination: Path,
) -> Path:

    temporary_path = None

    try:

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix="document_",
            dir=destination.parent,
            delete=False,
        ) as temporary_file:

            temporary_path = Path(temporary_file.name)

            json.dump(
                payload,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )

            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(
            temporary_path,
            destination,
        )

        return destination

    except Exception as exc:

        if temporary_path is not None:

            try:
                temporary_path.unlink(missing_ok=True)

            except OSError:
                logger.exception(
                    "Unable to remove temporary artifact."
                )

        raise DocumentProcessingStorageError(
            "Unable to save the unified document artifact."
        ) from exc


# ==========================================================
# UNIFIED ARTIFACT GENERATION
# ==========================================================

def _build_unified_artifact(
    document_id: str,
    native_result,
    ocr_result,
    cleaning_result,
    structure,
    chunking_result,
    chunking_artifact_path,
    started_at: datetime,
    completed_at: datetime,
) -> dict:

    pages = [
        _to_dict(page)
        for page in ocr_result.pages
    ]

    return {
        "document_id": document_id,

        "processing_status": "completed",

        "processing_started_at": _timestamp(
            started_at
        ),

        "processing_completed_at": _timestamp(
            completed_at
        ),

        "page_count": ocr_result.page_count,

        "total_characters": ocr_result.total_characters,

        "total_words": ocr_result.total_words,

        "pages_with_text": ocr_result.pages_with_text,

        "extraction_method": "native_and_ocr",

        "quality_status": ocr_result.quality_status,

        "ocr_pages": ocr_result.ocr_pages,

        "failed_pages": ocr_result.failed_pages,

        "average_ocr_confidence": (
            ocr_result.average_ocr_confidence
        ),

        "warnings": ocr_result.warnings,

        "pages": pages,

        "native_extraction": _to_dict(
            native_result
        ),

        "text_cleaning": _to_dict(
            cleaning_result
        ),

        "document_structure": structure,

        "chunking": _to_dict(chunking_result),

        "chunking_artifact_path": str(
            chunking_artifact_path
        ),
    }


# ==========================================================
# PHASE 7.8 - PROCESSING STATUS AND FAILURE RECOVERY
# ==========================================================

def _safe_failure_message(exc: Exception) -> str:
    """
    Return a controlled failure message.

    Avoid exposing internal paths, database details,
    or arbitrary exception messages.
    """

    if isinstance(exc, DocumentProcessingStorageError):
        return "Document processing artifact storage failed."

    if isinstance(exc, PDFExtractionError):
        return "PDF text extraction failed."

    if isinstance(exc, OCRProcessingError):
        return "OCR processing failed."

    if isinstance(exc, DocumentProcessingError):
        return str(exc)[:500]

    return "An unexpected document processing error occurred."


def _persist_processing_failure(
    *,
    document_record,
    db: Session,
    exc: Exception,
) -> None:
    """
    Persist failure status and completion timestamp.
    """

    db.rollback()

    document_record.processing_status = "failed"

    document_record.processing_completed_at = _utc_now()

    document_record.processing_error = _safe_failure_message(
        exc
    )

    db.add(document_record)

    db.commit()


# ==========================================================
# DOCUMENT PROCESSING PIPELINE
# ==========================================================

def process_document(
    *,
    document_record,
    pdf_path: Path,
    db: Session,
    document_settings: DocumentSettings,
    ocr_settings: OCRSettings,
    cleaning_settings: TextCleaningSettings | None = None,
    chunking_settings: ChunkingSettings | None = None,
) -> DocumentProcessingResult:
    """
    Complete document processing workflow.

    Phase 7.17 improvements:
    - Atomic document processing claim.
    - Prevents multiple workers from processing the same document.
    - Processing attempt count is managed by the status service.
    - Existing extraction, OCR, cleaning, structure,
      chunking, artifact generation and failure recovery
      are preserved.

    Phase 7.21 improvements:
    - Processing start/completion/failure metrics.
    - Per-stage execution timing.
    - Per-stage failure tracking.
    - Structured observability logging.
    """

    # ------------------------------------------------------
    # STEP 1: Validate document UUID
    # ------------------------------------------------------

    try:

        document_id = str(
            UUID(str(document_record.id))
        )

    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:

        raise DocumentProcessingError(
            "Document record contains an invalid UUID."
        ) from exc

    # ------------------------------------------------------
    # STEP 2: Initialize and validate configuration
    # ------------------------------------------------------

    cleaning_settings = (
        cleaning_settings or TextCleaningSettings()
    )

    chunking_settings = (
        chunking_settings or ChunkingSettings()
    )

    _validate_processing_configuration(
        document_settings=document_settings,
        ocr_settings=ocr_settings,
        cleaning_settings=cleaning_settings,
        chunking_settings=chunking_settings,
    )

    # ------------------------------------------------------
    # STEP 3: Atomically claim processing
    # ------------------------------------------------------

    try:
        claimed_document = claim_document_for_processing(
            db=db,
            document_id=UUID(document_id),
        )

    except DocumentAlreadyClaimedError as exc:
        raise DocumentProcessingAlreadyClaimedError(
            "Document is already processing or cannot be processed."
        ) from exc

    except Exception as exc:
        raise DocumentProcessingDatabaseError(
            "Unable to claim document for processing."
        ) from exc

    document_record = claimed_document

    started_at = (
        document_record.processing_started_at
        or _utc_now()
    )

    processing_attempt = getattr(
        document_record,
        "processing_attempts",
        0,
    )

    # Phase 7.21: Record processing start.
    document_observability.record_processing_started(
        document_id=document_id,
        attempt=processing_attempt,
    )

    artifact_path = None
    cleaning_artifact_path = None
    structure_artifact_path = None
    chunking_artifact_path = None

    try:

        # --------------------------------------------------
        # STEP 5: Validate registered PDF and integrity
        # --------------------------------------------------

        with observe_processing_stage(
            document_id=document_id,
            stage="stored_document_validation",
        ):
            pdf_path = _validate_stored_document(
                document_record=document_record,
                pdf_path=pdf_path,
                document_settings=document_settings,
            )

        # --------------------------------------------------
        # STEP 6: Native PDF text extraction
        # --------------------------------------------------

        logger.info(
            "Starting native PDF extraction for document %s.",
            document_id,
        )

        with observe_processing_stage(
            document_id=document_id,
            stage="native_pdf_extraction",
        ):
            native_result = extract_pdf_text(
                pdf_path=pdf_path,
                document_id=document_id,
                settings=document_settings,
            )

        # --------------------------------------------------
        # STEP 7: Native + OCR processing
        # --------------------------------------------------

        logger.info(
            "Starting OCR processing for document %s.",
            document_id,
        )

        with observe_processing_stage(
            document_id=document_id,
            stage="ocr_processing",
        ):
            ocr_result = extract_pdf_with_ocr(
                pdf_path=pdf_path,
                document_id=document_id,
                settings=ocr_settings,
                max_pages=document_settings.max_pages,
            )

        # --------------------------------------------------
        # STEP 8: Text cleaning and normalization
        # --------------------------------------------------

        logger.info(
            "Starting text cleaning for document %s.",
            document_id,
        )

        with observe_processing_stage(
            document_id=document_id,
            stage="text_cleaning",
        ):
            cleaning_result = clean_document_text(
                document_id=document_id,
                pages=ocr_result.pages,
                settings=cleaning_settings,
            )

        with observe_processing_stage(
            document_id=document_id,
            stage="cleaned_text_artifact_storage",
        ):
            cleaning_artifact_path = save_cleaned_text_artifact(
                result=cleaning_result,
                storage_root=document_settings.storage_root,
            )

        # --------------------------------------------------
        # STEP 9: Build cleaned OCR page results
        # --------------------------------------------------

        if len(ocr_result.pages) != len(cleaning_result.pages):

            raise DocumentProcessingError(
                "OCR and cleaned page counts do not match."
            )

        cleaned_ocr_pages = []

        for original_page, cleaned_page in zip(
            ocr_result.pages,
            cleaning_result.pages,
        ):

            cleaned_ocr_pages.append(
                _replace_object(
                    original_page,
                    text=cleaned_page.text,
                    character_count=len(cleaned_page.text),
                    word_count=len(cleaned_page.text.split()),
                )
            )

        cleaned_ocr_result = _replace_object(
            ocr_result,

            pages=cleaned_ocr_pages,

            total_characters=sum(
                page.character_count
                for page in cleaned_ocr_pages
            ),

            total_words=sum(
                page.word_count
                for page in cleaned_ocr_pages
            ),

            pages_with_text=sum(
                bool(page.text.strip())
                for page in cleaned_ocr_pages
            ),
        )

        # --------------------------------------------------
        # STEP 10: Document structure extraction
        # --------------------------------------------------

        logger.info(
            "Starting document structure extraction for document %s.",
            document_id,
        )

        with observe_processing_stage(
            document_id=document_id,
            stage="document_structure_extraction",
        ):
            structure, structure_artifact_path = (
                process_document_structure(
                    pdf_path=pdf_path,
                    document_id=document_id,
                    storage_root=document_settings.storage_root,
                    ocr_pages=cleaned_ocr_result.pages,
                )
            )

        # --------------------------------------------------
        # STEP 11: Document chunking
        # --------------------------------------------------

        logger.info(
            "Starting document chunking for document %s.",
            document_id,
        )

        with observe_processing_stage(
            document_id=document_id,
            stage="document_chunking",
        ):
            chunking_result = chunk_document_pages(
                document_id=document_id,
                pages=cleaned_ocr_result.pages,
                settings=chunking_settings,
            )

        with observe_processing_stage(
            document_id=document_id,
            stage="chunking_artifact_storage",
        ):
            chunking_artifact_path = save_chunking_artifact(
                result=chunking_result,
                storage_root=document_settings.storage_root,
            )

        # --------------------------------------------------
        # STEP 11.5: Persist chunks and generate embeddings
        # --------------------------------------------------

        logger.info(
            "Starting document indexing for document %s.",
            document_id,
        )

        with observe_processing_stage(
            document_id=document_id,
            stage="document_indexing",
        ):
            indexing_result = index_document_chunks(
                db=db,
                chunking_result=chunking_result,
                batch_size=32,
            )

        logger.info(
            (
                "Document indexing finished. "
                "Document=%s, chunks=%s, embeddings_ready=%s, "
                "embeddings_failed=%s, skipped=%s, error=%s"
            ),
            document_id,
            indexing_result.persisted_chunks,
            indexing_result.embeddings_ready,
            indexing_result.embeddings_failed,
            indexing_result.embeddings_skipped,
            indexing_result.indexing_error,
        )

        # --------------------------------------------------
        # STEP 12: Generate unified artifact
        # --------------------------------------------------

        completed_at = _utc_now()

        with observe_processing_stage(
            document_id=document_id,
            stage="unified_artifact_serialization",
        ):
            artifact = _build_unified_artifact(
                document_id=document_id,
                native_result=native_result,
                ocr_result=cleaned_ocr_result,
                cleaning_result=cleaning_result,
                structure=structure,
                chunking_result=chunking_result,
                chunking_artifact_path=chunking_artifact_path,
                started_at=started_at,
                completed_at=completed_at,
            )

        processed_directory = (
            Path(document_settings.storage_root)
            / "processed"
        )

        artifact_path = (
            processed_directory
            / f"{document_id}_processed.json"
        )

        with observe_processing_stage(
            document_id=document_id,
            stage="unified_artifact_storage",
        ):
            _save_json_atomically(
                artifact,
                artifact_path,
            )

        # --------------------------------------------------
        # STEP 13: Persist successful processing
        # --------------------------------------------------

        document_record.page_count = (
            cleaned_ocr_result.page_count
        )

        document_record.processing_status = "completed"

        document_record.processing_completed_at = completed_at

        document_record.processing_error = None

        db.add(document_record)

        db.commit()

        db.refresh(document_record)

        duration = (
            completed_at - started_at
        ).total_seconds()

        # Phase 7.21: Record successful processing.
        document_observability.record_processing_completed(
            document_id=document_id,
            duration_seconds=duration,
            page_count=cleaned_ocr_result.page_count,
            attempt=getattr(
                document_record,
                "processing_attempts",
                processing_attempt,
            ),
        )

        logger.info(
            "Document %s processing completed successfully. "
            "Pages: %s, attempts: %s.",
            document_id,
            cleaned_ocr_result.page_count,
            document_record.processing_attempts,
        )

        # --------------------------------------------------
        # STEP 14: Prepare processing result
        # --------------------------------------------------

        combined_warnings = list(
            cleaned_ocr_result.warnings
        )

        combined_warnings.extend(
            cleaning_result.warnings
        )

        return DocumentProcessingResult(

            document_id=document_id,

            processing_status="completed",

            processing_started_at=_timestamp(
                started_at
            ),

            processing_completed_at=_timestamp(
                completed_at
            ),

            processing_duration_seconds=round(
                duration,
                3,
            ),

            page_count=cleaned_ocr_result.page_count,

            total_characters=(
                cleaned_ocr_result.total_characters
            ),

            total_words=(
                cleaned_ocr_result.total_words
            ),

            pages_with_text=(
                cleaned_ocr_result.pages_with_text
            ),

            extraction_method="native_and_ocr",

            quality_status=(
                cleaned_ocr_result.quality_status
            ),

            artifact_path=str(artifact_path),

            warnings=combined_warnings,
        )

    except Exception as exc:

        # A duplicate worker must not mark the active worker's
        # document as failed.
        if isinstance(
            exc,
            DocumentProcessingAlreadyClaimedError,
        ):
            raise

        # Phase 7.21: Record processing failure.
        document_observability.record_processing_failed(
            document_id=document_id,
            stage="document_processing_pipeline",
            error_type=type(exc).__name__,
            attempt=getattr(
                document_record,
                "processing_attempts",
                processing_attempt,
            ),
        )

        logger.error(
            "Document %s processing failed: %s",
            document_id,
            type(exc).__name__,
        )

        # --------------------------------------------------
        # STEP 15: Remove incomplete artifacts
        # --------------------------------------------------

        for path in (
            artifact_path,
            cleaning_artifact_path,
            structure_artifact_path,
            chunking_artifact_path,
        ):

            if path is not None:

                try:

                    Path(path).unlink(
                        missing_ok=True
                    )

                except OSError:

                    logger.exception(
                        "Unable to remove incomplete artifact."
                    )

        # --------------------------------------------------
        # STEP 16: Persist failure information
        # --------------------------------------------------

        try:

            _persist_processing_failure(
                document_record=document_record,
                db=db,
                exc=exc,
            )

        except Exception:

            db.rollback()

            logger.exception(
                "Unable to persist document processing failure."
            )

        # --------------------------------------------------
        # STEP 17: Handle known exceptions
        # --------------------------------------------------

        if isinstance(exc, DocumentProcessingError):
            raise

        if isinstance(
            exc,
            (
                PDFExtractionError,
                OCRProcessingError,
            ),
        ):

            raise DocumentProcessingError(
                "Document text extraction or OCR processing failed."
            ) from exc

        # --------------------------------------------------
        # STEP 18: Handle unexpected exceptions
        # --------------------------------------------------

        logger.exception(
            "Unexpected document processing failure."
        )

        raise DocumentProcessingError(
            "Unexpected document processing failure."
        ) from exc