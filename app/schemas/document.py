import uuid

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Public document metadata returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    original_filename: str

    mime_type: str

    file_size_bytes: int

    checksum_sha256: str

    page_count: int | None

    processing_status: str

    processing_attempts: int

    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated document listing."""

    items: list[DocumentResponse]

    total: int

    offset: int

    limit: int


class DocumentStatusResponse(BaseModel):
    """Document processing status."""

    document_id: uuid.UUID

    processing_status: str

    processing_attempts: int

    processing_started_at: datetime | None

    processing_completed_at: datetime | None

    processing_error: str | None

    page_count: int | None