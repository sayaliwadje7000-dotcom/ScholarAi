import logging
import uuid

from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user

from app.core.document_config import document_settings
from app.core.ocr_config import ocr_settings

from app.database.session import (
    SessionLocal,
    get_db,
)

from app.models.document import Document
from app.models.user import User

from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentStatusResponse,
)

from app.services.document_database_service import (
    store_and_register_document,
    get_user_document,
    list_user_documents,
    count_user_documents,
    DocumentNotFoundError,
    DocumentPersistenceError,
    DocumentConsistencyError,
)

from app.services.document_storage_service import (
    DocumentStorageError,
    DocumentValidationError,
    DocumentSizeError,
    get_document_path,
)

from app.services.document_processing_service import (
    process_document,
)


logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# FILE READING
# ============================================================

async def read_upload_with_limit(
    upload: UploadFile,
    maximum_size: int,
) -> bytes:
    """
    Read an uploaded file in bounded chunks.

    The extra byte allows the function to detect an oversized
    upload without reading the entire file into memory.
    """

    chunks = []
    total_size = 0

    chunk_size = 1024 * 1024

    while True:

        remaining = maximum_size + 1 - total_size

        if remaining <= 0:
            raise DocumentSizeError(
                "The uploaded document exceeds the permitted size."
            )

        chunk = await upload.read(
            min(chunk_size, remaining)
        )

        if not chunk:
            break

        total_size += len(chunk)

        if total_size > maximum_size:
            raise DocumentSizeError(
                "The uploaded document exceeds the permitted size."
            )

        chunks.append(chunk)

    return b"".join(chunks)


# ============================================================
# BACKGROUND PROCESSING
# ============================================================

def process_document_background(
    document_id: uuid.UUID,
) -> None:
    """
    Process a document using an independent database session.

    FastAPI BackgroundTasks are used for the current integration.
    This is not a durable job queue.
    """

    db = SessionLocal()

    try:

        document = db.get(
            Document,
            document_id,
        )

        if document is None:
            logger.error(
                "Background processing could not find document %s.",
                document_id,
            )
            return

        if document.processing_status not in {
            "pending",
            "failed",
        }:
            logger.info(
                "Skipping document %s because its status is %s.",
                document_id,
                document.processing_status,
            )
            return

        pdf_path = get_document_path(
            document.storage_key,
            document_settings,
        )

        process_document(
            document_record=document,
            pdf_path=Path(pdf_path),
            db=db,
            document_settings=document_settings,
            ocr_settings=ocr_settings,
        )

        logger.info(
            "Document %s processing completed.",
            document_id,
        )

    except Exception:

        logger.exception(
            "Background processing failed for document %s.",
            document_id,
        )

        db.rollback()

    finally:
        db.close()


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an academic PDF",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF, persist its metadata and schedule processing.

    The document owner is taken exclusively from the
    authenticated user dependency.
    """

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A filename is required.",
        )

    try:

        content = await read_upload_with_limit(
            file,
            document_settings.max_file_size_bytes,
        )

        document = store_and_register_document(
            db=db,
            user_id=current_user.id,
            content=content,
            original_filename=file.filename,
            content_type=file.content_type,
            settings=document_settings,
        )

        background_tasks.add_task(
            process_document_background,
            document.id,
        )

        return document

    except DocumentSizeError as exc:

        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    except DocumentValidationError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except DocumentConsistencyError as exc:

        logger.exception(
            "Document storage/database consistency failure."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Document registration failed. "
                "Storage reconciliation may be required."
            ),
        ) from exc

    except DocumentPersistenceError as exc:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to save document metadata.",
        ) from exc

    except DocumentStorageError as exc:

        logger.exception(
            "Document storage operation failed."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document storage operation failed.",
        ) from exc

    finally:
        await file.close()


# ============================================================
# LIST USER DOCUMENTS
# ============================================================

@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List uploaded documents",
)
def get_documents(
    offset: int = Query(
        0,
        ge=0,
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a paginated list of the current user's documents."""

    documents = list_user_documents(
        db=db,
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )

    total = count_user_documents(
        db=db,
        user_id=current_user.id,
    )

    return DocumentListResponse(
        items=documents,
        total=total,
        offset=offset,
        limit=limit,
    )


# ============================================================
# GET DOCUMENT METADATA
# ============================================================

@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Retrieve document metadata",
)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve metadata only for a document owned by the user."""

    try:

        return get_user_document(
            db=db,
            document_id=document_id,
            user_id=current_user.id,
        )

    except DocumentNotFoundError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from exc


# ============================================================
# GET DOCUMENT PROCESSING STATUS
# ============================================================

@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Retrieve document processing status",
)
def get_document_status(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return processing information for an owned document."""

    try:

        document = get_user_document(
            db=db,
            document_id=document_id,
            user_id=current_user.id,
        )

    except DocumentNotFoundError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from exc

    return DocumentStatusResponse(
        document_id=document.id,
        processing_status=document.processing_status,
        processing_attempts=document.processing_attempts,
        processing_started_at=document.processing_started_at,
        processing_completed_at=document.processing_completed_at,
        processing_error=document.processing_error,
        page_count=document.page_count,
    )