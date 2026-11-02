from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserResourceInteraction(Base):
    __tablename__ = "user_resource_interactions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    resource_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("study_resources.id", ondelete="CASCADE"),
        nullable=False,
    )

    interaction_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    rating: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    interaction_metadata: Mapped[dict] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="resource_interactions",
    )

    resource: Mapped["StudyResource"] = relationship(
        "StudyResource",
        back_populates="user_interactions",
    )

    __table_args__ = (
        CheckConstraint(
            """
            interaction_type IN (
                'view',
                'click',
                'save',
                'rate',
                'complete'
            )
            """,
            name="ck_user_resource_interactions_valid_type",
        ),
        CheckConstraint(
            """
            (
                interaction_type = 'rate'
                AND rating IS NOT NULL
                AND rating BETWEEN 1 AND 5
            )
            OR
            (
                interaction_type <> 'rate'
                AND rating IS NULL
            )
            """,
            name="ck_user_resource_interactions_valid_rating",
        ),
        CheckConstraint(
            """
            duration_seconds IS NULL
            OR duration_seconds >= 0
            """,
            name="ck_user_resource_interactions_valid_duration",
        ),
        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_user_resource_interactions_metadata_object",
        ),
        Index(
            "ix_user_resource_interactions_user_id",
            "user_id",
        ),
        Index(
            "ix_user_resource_interactions_resource_id",
            "resource_id",
        ),
        Index(
            "ix_user_resource_interactions_interaction_type",
            "interaction_type",
        ),
        Index(
            "ix_user_resource_interactions_occurred_at",
            "occurred_at",
        ),
        Index(
            "ix_user_resource_interactions_user_occurred",
            "user_id",
            "occurred_at",
        ),
        Index(
            "ix_user_resource_interactions_user_resource",
            "user_id",
            "resource_id",
        ),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid4())
        kwargs.setdefault("interaction_metadata", {})

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<UserResourceInteraction("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"resource_id={self.resource_id}, "
            f"interaction_type={self.interaction_type!r})>"
        )