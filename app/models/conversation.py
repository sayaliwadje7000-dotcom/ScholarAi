import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Conversation(Base):
    """
    Represents a conversation between a ScholarAI user
    and the AI assistant.
    """

    __tablename__ = "conversations"

    __table_args__ = (
        Index(
            "ix_conversations_user_id",
            "user_id",
        ),
        Index(
            "ix_conversations_user_updated",
            "user_id",
            "updated_at",
        ),
    )

    # Primary key.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda context: uuid.uuid4(),
    )

    # Owner of the conversation.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_conversations_user_id_users",
        ),
        nullable=False,
    )

    # Optional conversation title.
    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # Archive status.
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # Creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Last modification timestamp.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationship with User.
    user: Mapped["User"] = relationship(
        "User",
        back_populates="conversations",
    )

    # Messages belonging to this conversation.
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return (
            f"<Conversation(id={self.id}, "
            f"user_id={self.user_id}, "
            f"title={self.title!r}, "
            f"is_archived={self.is_archived})>"
        )