import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Message(Base):
    """
    Represents an individual message in a ScholarAI conversation.
    """

    __tablename__ = "messages"

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="ck_messages_valid_role",
        ),
        CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="ck_messages_nonnegative_token_count",
        ),
        Index(
            "ix_messages_conversation_created",
            "conversation_id",
            "created_at",
        ),
    )

    # Primary key.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda context: uuid.uuid4(),
    )

    # Conversation to which this message belongs.
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE",
            name="fk_messages_conversation_id_conversations",
        ),
        nullable=False,
    )

    # Message sender.
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Message content.
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Number of tokens used by the message.
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Message creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Parent conversation.
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, "
            f"conversation_id={self.conversation_id}, "
            f"role='{self.role}')>"
        )