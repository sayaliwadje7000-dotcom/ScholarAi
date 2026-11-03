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
    Supports dataclasses, SimpleNamespace, dictionaries,
    lists, tuples, UUIDs, Paths and datetime objects.
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
    }


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
) -> DocumentProcessingResult:

    """
    Complete document processing workflow.

    1. Validate document.
    2. Mark document as processing.
    3. Extract native PDF text.
    4. Perform OCR.
    5. Clean and normalize extracted text.
    6. Extract document structure.
    7. Generate unified JSON artifact.
    8. Update database status.
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
    # STEP 2: Validate PDF
    # ------------------------------------------------------

    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():
        raise DocumentProcessingError(
            "Stored PDF file does not exist."
        )

    started_at = _utc_now()

    artifact_path = None
    cleaning_artifact_path = None
    structure_artifact_path = None

    # ------------------------------------------------------
    # STEP 3: Mark document as processing
    # ------------------------------------------------------

    try:
        document_record.processing_status = "processing"

        db.add(document_record)
        db.commit()

    except Exception as exc:
        db.rollback()

        raise DocumentProcessingDatabaseError(
            "Unable to update document processing status."
        ) from exc

    try:

        # --------------------------------------------------
        # STEP 4: Native PDF text extraction
        # --------------------------------------------------

        native_result = extract_pdf_text(
            pdf_path=pdf_path,
            document_id=document_id,
            settings=document_settings,
        )

        # --------------------------------------------------
        # STEP 5: Native + OCR processing
        # OCR runs only once.
        # --------------------------------------------------

        ocr_result = extract_pdf_with_ocr(
            pdf_path=pdf_path,
            document_id=document_id,
            settings=ocr_settings,
            max_pages=document_settings.max_pages,
        )

        # --------------------------------------------------
        # STEP 6: PHASE 7.7
        # Text cleaning and normalization
        # --------------------------------------------------

        cleaning_result = clean_document_text(
            document_id=document_id,
            pages=ocr_result.pages,
            settings=TextCleaningSettings(),
        )

        cleaning_artifact_path = save_cleaned_text_artifact(
            result=cleaning_result,
            storage_root=document_settings.storage_root,
        )

        # --------------------------------------------------
        # STEP 7: Build cleaned OCR page results
        # Preserve original OCR metadata.
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
        # STEP 8: PHASE 7.6
        # Document structure extraction
        # Reuse cleaned OCR results.
        # --------------------------------------------------

        structure, structure_artifact_path = (
            process_document_structure(
                pdf_path=pdf_path,
                document_id=document_id,
                storage_root=document_settings.storage_root,
                ocr_pages=cleaned_ocr_result.pages,
            )
        )

        # --------------------------------------------------
        # STEP 9: Generate unified artifact
        # --------------------------------------------------

        completed_at = _utc_now()

        artifact = _build_unified_artifact(
            document_id=document_id,
            native_result=native_result,
            ocr_result=cleaned_ocr_result,
            cleaning_result=cleaning_result,
            structure=structure,
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

        _save_json_atomically(
            artifact,
            artifact_path,
        )

        # --------------------------------------------------
        # STEP 10: Update database metadata
        # --------------------------------------------------

        document_record.page_count = (
            cleaned_ocr_result.page_count
        )

        document_record.processing_status = "completed"

        db.add(document_record)
        db.commit()
        db.refresh(document_record)

        # --------------------------------------------------
        # STEP 11: Return processing result
        # --------------------------------------------------

        duration = (
            completed_at - started_at
        ).total_seconds()

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

        # --------------------------------------------------
        # STEP 12: Roll back database transaction
        # --------------------------------------------------

        db.rollback()

        # --------------------------------------------------
        # STEP 13: Remove incomplete artifacts
        # --------------------------------------------------

        for path in (
            artifact_path,
            cleaning_artifact_path,
            structure_artifact_path,
        ):

            if path is not None:
                try:
                    Path(path).unlink(missing_ok=True)

                except OSError:
                    logger.exception(
                        "Unable to remove incomplete artifact."
                    )

        # --------------------------------------------------
        # STEP 14: Mark document as failed
        # --------------------------------------------------

        try:
            document_record.processing_status = "failed"

            db.add(document_record)
            db.commit()

        except Exception:
            db.rollback()

            logger.exception(
                "Failed to update document status after processing failure."
            )

        # --------------------------------------------------
        # STEP 15: Handle known exceptions
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
        # STEP 16: Handle unexpected exceptions
        # --------------------------------------------------

        logger.exception(
            "Unexpected document processing failure."
        )

        raise DocumentProcessingError(
            "Unexpected document processing failure."
        ) from exc