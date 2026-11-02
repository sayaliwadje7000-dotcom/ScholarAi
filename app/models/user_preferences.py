import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    text,
)

from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.ext.mutable import MutableList

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserPreferences(Base):
    """
    Stores personalized learning preferences
    and settings for a ScholarAI user.
    """

    __tablename__ = "user_preferences"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_user_preferences_user_id",
        ),
        CheckConstraint(
            "jsonb_typeof(preferred_subjects) = 'array'",
            name="ck_user_preferences_subjects_array",
        ),
        CheckConstraint(
            "jsonb_typeof(learning_goals) = 'array'",
            name="ck_user_preferences_goals_array",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_user_preferences_user_id_users",
        ),
        nullable=False,
    )

    preferred_language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    education_level: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    preferred_subjects: Mapped[list] = mapped_column(
        MutableList.as_mutable(JSONB),
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    learning_goals: Mapped[list] = mapped_column(
        MutableList.as_mutable(JSONB),
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    notification_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="preferences",
    )

    def __repr__(self) -> str:
        return (
            f"<UserPreferences("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"preferred_language={self.preferred_language!r}"
            f")>"
        )