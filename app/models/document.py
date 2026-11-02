import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Document(Base):
    """
    Represents an uploaded academic document
    belonging to a ScholarAI user.

    The database stores document metadata.
    Actual document files are stored externally.
    """

    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint(
            "storage_key",
            name="uq_documents_storage_key",
        ),

        CheckConstraint(
            "file_size_bytes > 0",
            name="ck_documents_positive_file_size",
        ),

        CheckConstraint(
            "page_count IS NULL OR page_count > 0",
            name="ck_documents_positive_page_count",
        ),

        CheckConstraint(
            "processing_status IN "
            "('pending', 'processing', 'completed', 'failed')",
            name="ck_documents_valid_processing_status",
        ),

        CheckConstraint(
            "checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_documents_valid_sha256",
        ),

        Index(
            "ix_documents_user_id",
            "user_id",
        ),

        Index(
            "ix_documents_processing_status",
            "processing_status",
        ),

        Index(
            "ix_documents_user_uploaded",
            "user_id",
            "uploaded_at",
        ),
    )

    # Primary key.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Document owner.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_documents_user_id_users",
        ),
        nullable=False,
    )

    # Original uploaded filename.
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Internal storage identifier.
    storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    # Document MIME type.
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # File size in bytes.
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # SHA-256 checksum.
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Number of pages.
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Document processing state.
    processing_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    # Upload timestamp.
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationship with User.
    user: Mapped["User"] = relationship(
        "User",
        back_populates="documents",
    )

    def __repr__(self) -> str:
        return (
            f"<Document("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"filename={self.original_filename!r}, "
            f"status={self.processing_status!r}"
            f")>"
        )