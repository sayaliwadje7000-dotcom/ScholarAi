from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RecommendationFeedback(Base):

    __tablename__ = "recommendation_feedback"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    recommendation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "recommendations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    feedback_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    recommendation: Mapped["Recommendation"] = relationship(
        "Recommendation",
        back_populates="feedback_entries",
    )

    __table_args__ = (

        UniqueConstraint(
            "recommendation_id",
            name="uq_recommendation_feedback_recommendation",
        ),

        CheckConstraint(
            """
            feedback_type IN (
                'helpful',
                'not_helpful',
                'irrelevant'
            )
            """,
            name="ck_recommendation_feedback_valid_type",
        ),

        Index(
            "ix_recommendation_feedback_recommendation_id",
            "recommendation_id",
        ),

        Index(
            "ix_recommendation_feedback_feedback_type",
            "feedback_type",
        ),

        Index(
            "ix_recommendation_feedback_created_at",
            "created_at",
        ),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid4())

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<RecommendationFeedback("
            f"id={self.id}, "
            f"recommendation_id={self.recommendation_id}, "
            f"feedback_type={self.feedback_type!r})>"
        )