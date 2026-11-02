import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)

from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.ext.mutable import MutableDict

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class LearningActivity(Base):
    """
    Represents an activity performed by a ScholarAI user.

    Activities may include document uploads, study sessions,
    AI questions, quiz attempts, and resource interactions.

    Additional activity information is stored in JSONB.
    """

    __tablename__ = "learning_activities"

    __table_args__ = (

        CheckConstraint(
            "length(trim(activity_type)) > 0",
            name="ck_learning_activities_nonempty_activity_type",
        ),

        CheckConstraint(
            "entity_type IS NULL OR length(trim(entity_type)) > 0",
            name="ck_learning_activities_valid_entity_type",
        ),

        CheckConstraint(
            """
            (entity_type IS NULL AND entity_id IS NULL)
            OR
            (entity_type IS NOT NULL AND entity_id IS NOT NULL)
            """,
            name="ck_learning_activities_entity_reference_pair",
        ),

        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_learning_activities_nonnegative_duration",
        ),

        Index(
            "ix_learning_activities_user_id",
            "user_id",
        ),

        Index(
            "ix_learning_activities_occurred_at",
            "occurred_at",
        ),

        Index(
            "ix_learning_activities_user_occurred",
            "user_id",
            "occurred_at",
        ),

        Index(
            "ix_learning_activities_entity",
            "entity_type",
            "entity_id",
        ),
    )

    # Primary key.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # User who performed the activity.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_learning_activities_user_id_users",
        ),
        nullable=False,
    )

    # Type of activity performed.
    activity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Type of associated entity.
    entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # ID of the associated entity.
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Duration of activity in seconds.
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Additional activity information.
    # Python attribute: activity_metadata
    # PostgreSQL column: metadata
    activity_metadata: Mapped[dict] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # Activity timestamp.
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationship with User.
    user: Mapped["User"] = relationship(
        "User",
        back_populates="learning_activities",
    )

    def __repr__(self) -> str:
        return (
            f"<LearningActivity("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"activity_type={self.activity_type!r}, "
            f"entity_type={self.entity_type!r}"
            f")>"
        )