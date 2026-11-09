from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.recommendation_context import (
    RecommendationContext,
)


class LearningGoalContext(BaseModel):
    """Normalized learning goal for personalization."""

    model_config = ConfigDict(frozen=True)

    goal_id: str | None = None

    title: str

    priority: str | None = None

    status: str = "active"

    progress_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    target_date: datetime | None = None


class BehavioralEvidenceSummary(BaseModel):
    """Aggregated behavioral evidence for one student."""

    model_config = ConfigDict(frozen=True)

    total_signals: int = Field(ge=0)

    positive_signals: int = Field(ge=0)

    negative_signals: int = Field(ge=0)

    neutral_signals: int = Field(ge=0)

    average_confidence: float = Field(
        ge=0,
        le=1,
    )

    average_signal_strength: float = Field(
        ge=-1,
        le=1,
    )

    evidence_coverage: float = Field(
        ge=0,
        le=1,
    )

    latest_activity_at: datetime | None = None


class FeedbackEvidenceSummary(BaseModel):
    """Explicit recommendation feedback summary."""

    model_config = ConfigDict(frozen=True)

    total_feedback: int = Field(ge=0)

    positive_feedback: int = Field(ge=0)

    negative_feedback: int = Field(ge=0)

    feedback_confidence: float = Field(
        ge=0,
        le=1,
    )


class PersonalizationConfidence(BaseModel):
    """Confidence and evidence sufficiency assessment."""

    model_config = ConfigDict(frozen=True)

    profile_confidence: float = Field(
        ge=0,
        le=1,
    )

    behavioral_confidence: float = Field(
        ge=0,
        le=1,
    )

    feedback_confidence: float = Field(
        ge=0,
        le=1,
    )

    overall_confidence: float = Field(
        ge=0,
        le=1,
    )

    evidence_count: int = Field(ge=0)

    is_sparse: bool

    confidence_level: str


class PersonalizedLearningContext(BaseModel):
    """
    Unified personalization context.

    Combines the existing recommendation context with
    structured goals, behavioral evidence, explicit
    feedback and confidence information.
    """

    model_config = ConfigDict(frozen=True)

    user_id: UUID

    context_version: str = "personalized-v1"

    recommendation_context: RecommendationContext

    learning_goals: list[LearningGoalContext] = Field(
        default_factory=list,
    )

    behavioral_evidence: BehavioralEvidenceSummary

    feedback_evidence: FeedbackEvidenceSummary

    personalization_confidence: PersonalizationConfidence

    generated_at: datetime

    data_sources: list[str] = Field(
        default_factory=list,
    )