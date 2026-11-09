from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecommendationFeedbackLabel(BaseModel):
    """
    A normalized training label derived from explicit feedback.
    """

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    resource_id: UUID

    # Preserve the integer label returned by the existing ML pipeline.
    label: int = Field(
        description="Existing ML training label, such as 1 or 0."
    )

    label_source: str = "explicit_feedback"

    source_event: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    observed_at: datetime
    
class RecommendationFeedbackInsight(BaseModel):
    """
    A normalized personalization insight derived from
    a student's explicit recommendation feedback.
    """

    model_config = ConfigDict(frozen=True)

    feedback_id: UUID
    recommendation_id: UUID

    user_id: UUID
    resource_id: UUID

    feedback_type: str

    signal_strength: float = Field(
        ge=-1.0,
        le=1.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    label: RecommendationFeedbackLabel

    occurred_at: datetime


class RecommendationFeedbackInsightCollection(BaseModel):
    """
    Collection of feedback insights for one student.
    """

    model_config = ConfigDict(frozen=True)

    user_id: UUID

    total_feedback: int = Field(
        ge=0,
    )

    positive_feedback: int = Field(
        ge=0,
    )

    negative_feedback: int = Field(
        ge=0,
    )

    insights: list[RecommendationFeedbackInsight]