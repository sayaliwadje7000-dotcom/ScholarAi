from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Recommendation(Base):

    __tablename__ = "recommendations"

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

    recommendation_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    rank_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="generated",
        server_default="generated",
    )

    algorithm_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="v1",
        server_default="v1",
    )

    recommendation_metadata: Mapped[dict] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="recommendations",
    )

    resource: Mapped["StudyResource"] = relationship(
        "StudyResource",
        back_populates="recommendations",
    )

    feedback_entries: Mapped[
        list["RecommendationFeedback"]
    ] = relationship(
        "RecommendationFeedback",
        back_populates="recommendation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RecommendationFeedback.created_at",
    )

    __table_args__ = (

        CheckConstraint(
            """
            recommendation_type IN (
                'personalized',
                'trending',
                'related',
                'popular',
                'continue_learning'
            )
            """,
            name="ck_recommendations_valid_type",
        ),

        CheckConstraint(
            "score >= 0 AND score <= 1",
            name="ck_recommendations_valid_score",
        ),

        CheckConstraint(
            "rank_position >= 1",
            name="ck_recommendations_valid_rank",
        ),

        CheckConstraint(
            """
            status IN (
                'generated',
                'presented',
                'clicked',
                'dismissed',
                'expired'
            )
            """,
            name="ck_recommendations_valid_status",
        ),

        CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_recommendations_reason_nonempty",
        ),

        CheckConstraint(
            "length(trim(algorithm_version)) > 0",
            name="ck_recommendations_algorithm_version_nonempty",
        ),

        CheckConstraint(
            "expires_at IS NULL OR expires_at > generated_at",
            name="ck_recommendations_valid_expiration",
        ),

        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_recommendations_metadata_object",
        ),

        Index(
            "ix_recommendations_user_id",
            "user_id",
        ),

        Index(
            "ix_recommendations_resource_id",
            "resource_id",
        ),

        Index(
            "ix_recommendations_status",
            "status",
        ),

        Index(
            "ix_recommendations_score",
            "score",
        ),

        Index(
            "ix_recommendations_generated_at",
            "generated_at",
        ),

        Index(
            "ix_recommendations_user_rank",
            "user_id",
            "rank_position",
        ),

        Index(
            "ix_recommendations_user_status",
            "user_id",
            "status",
        ),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid4())
        kwargs.setdefault("recommendation_metadata", {})
        kwargs.setdefault("status", "generated")
        kwargs.setdefault("algorithm_version", "v1")

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<Recommendation("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"resource_id={self.resource_id}, "
            f"score={self.score}, "
            f"status={self.status!r})>"
        )