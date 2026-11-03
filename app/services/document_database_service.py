import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.document_config import DocumentSettings
from app.models.document import Document

from app.services.document_storage_service import (
    StoredDocument,
    save_document,
    delete_document,
)


logger = logging.getLogger(__name__)


# ============================================================
# EXCEPTIONS
# ============================================================

class DocumentDatabaseError(Exception):
    """Base exception for document database operations."""


class DocumentNotFoundError(DocumentDatabaseError):
    """Raised when a document does not exist or is inaccessible."""


class DocumentPersistenceError(DocumentDatabaseError):
    """Raised when document metadata cannot be persisted."""


class DocumentConsistencyError(DocumentDatabaseError):
    """Raised when storage and database consistency cannot be restored."""


# ============================================================
# DOCUMENT PERSISTENCE
# ============================================================

def create_document_record(
    *,
    db: Session,
    user_id: uuid.UUID,
    stored_document: StoredDocument,
) -> Document:
    """
    Create a database record for an already stored PDF.

    The physical PDF must be saved before calling this function.
    """

    if not isinstance(user_id, uuid.UUID):
        raise ValueError("A valid user UUID is required.")

    if not isinstance(stored_document, StoredDocument):
        raise ValueError("A valid StoredDocument instance is required.")

    document = Document(
        id=stored_document.document_id,
        user_id=user_id,
        original_filename=stored_document.original_filename,
        storage_key=stored_document.storage_key,
        mime_type=stored_document.mime_type,
        file_size_bytes=stored_document.file_size_bytes,
        checksum_sha256=stored_document.checksum_sha256,
        page_count=stored_document.page_count,
        processing_status="pending",
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

        return document

    except SQLAlchemyError as exc:
        db.rollback()

        logger.exception(
            "Database persistence failed for document %s.",
            stored_document.document_id,
        )

        raise DocumentPersistenceError(
            "Unable to persist document metadata."
        ) from exc


# ============================================================
# COMPLETE STORAGE + DATABASE OPERATION
# ============================================================

def store_and_register_document(
    *,
    db: Session,
    user_id: uuid.UUID,
    content: bytes,
    original_filename: str,
    content_type: str | None = None,
    settings: DocumentSettings | None = None,
) -> Document:
    """
    Store a PDF physically and register its metadata in PostgreSQL.

    If database persistence fails, attempt to remove the physical
    file so an unregistered document is not left behind.
    """

    if not isinstance(user_id, uuid.UUID):
        raise ValueError("A valid user UUID is required.")

    if settings is None:
        stored_document = save_document(
            content=content,
            original_filename=original_filename,
            content_type=content_type,
        )
    else:
        stored_document = save_document(
            content=content,
            original_filename=original_filename,
            content_type=content_type,
            settings=settings,
        )

    try:
        return create_document_record(
            db=db,
            user_id=user_id,
            stored_document=stored_document,
        )

    except DocumentPersistenceError:
        try:
            if settings is None:
                delete_document(
                    stored_document.storage_key,
                )
            else:
                delete_document(
                    stored_document.storage_key,
                    settings=settings,
                )

        except Exception as cleanup_error:
            logger.exception(
                "Database persistence failed and physical-file "
                "cleanup also failed for document %s.",
                stored_document.document_id,
            )

            raise DocumentConsistencyError(
                "Document registration failed and its physical "
                "file could not be cleaned up. Manual reconciliation "
                "is required."
            ) from cleanup_error

        raise


# ============================================================
# DOCUMENT RETRIEVAL
# ============================================================

def get_document_by_id(
    *,
    db: Session,
    document_id: uuid.UUID,
) -> Document:
    """Retrieve a document using its unique identifier."""

    statement = select(Document).where(
        Document.id == document_id
    )

    document = db.scalar(statement)

    if document is None:
        raise DocumentNotFoundError(
            "The requested document was not found."
        )

    return document


# ============================================================
# OWNER-SCOPED DOCUMENT RETRIEVAL
# ============================================================

def get_user_document(
    *,
    db: Session,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """
    Retrieve a document only if it belongs to the specified user.

    A document owned by another user is treated as not found.
    """

    statement = select(Document).where(
        Document.id == document_id,
        Document.user_id == user_id,
    )

    document = db.scalar(statement)

    if document is None:
        raise DocumentNotFoundError(
            "The requested document was not found."
        )

    return document


# ============================================================
# USER DOCUMENT LISTING
# ============================================================

def list_user_documents(
    *,
    db: Session,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 20,
) -> list[Document]:
    """
    Retrieve a paginated list of documents belonging to a user.

    Newest documents are returned first.
    """

    if offset < 0:
        raise ValueError("Offset cannot be negative.")

    if not 1 <= limit <= 100:
        raise ValueError(
            "Limit must be between 1 and 100."
        )

    statement = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(
            Document.uploaded_at.desc(),
            Document.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return list(
        db.scalars(statement).all()
    )


# ============================================================
# DOCUMENT COUNT
# ============================================================

def count_user_documents(
    *,
    db: Session,
    user_id: uuid.UUID,
) -> int:
    """Return the total number of documents owned by a user."""

    statement = (
        select(func.count())
        .select_from(Document)
        .where(Document.user_id == user_id)
    )

    return int(
        db.scalar(statement) or 0
    )