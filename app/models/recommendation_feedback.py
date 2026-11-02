import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
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

    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    recommendation: Mapped["Recommendation"] = relationship(
        "Recommendation",
        back_populates="feedback_entries",
    )

    __table_args__ = (
        CheckConstraint(
            "feedback_type IN "
            "('helpful', 'not_helpful', 'irrelevant')",
            name="ck_recommendation_feedback_valid_type",
        ),

        UniqueConstraint(
            "recommendation_id",
            name="uq_recommendation_feedback_recommendation_id",
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
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self):
        return (
            f"<RecommendationFeedback("
            f"id={self.id}, "
            f"recommendation_id={self.recommendation_id}, "
            f"feedback_type={self.feedback_type}"
            f")>"
        )