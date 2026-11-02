
import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    func,
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    """
    Represents a registered ScholarAI user.
    """

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint(
            "email",
            name="uq_users_email",
        ),
        Index(
            "ix_users_email",
            "email",
        ),
    )

    # Primary key.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: uuid.uuid4(),
    )

    # User's full name.
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    # Email address.
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Account activation status.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Account creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Last account update timestamp.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Conversations owned by this user.
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One-to-one user preferences relationship.
    preferences: Mapped["UserPreferences | None"] = relationship(
        "UserPreferences",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )

    # Documents uploaded by this user.
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Learning activities performed by this user.
    learning_activities: Mapped[list["LearningActivity"]] = relationship(
        "LearningActivity",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LearningActivity.occurred_at",
    )

    # Resource interactions performed by this user.
    resource_interactions: Mapped[
        list["UserResourceInteraction"]
    ] = relationship(
        "UserResourceInteraction",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="UserResourceInteraction.occurred_at",
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, "
            f"email='{self.email}', "
            f"is_active={self.is_active})>"
        )

