from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvaluationSegment(str, Enum):
    NO_DATA = "no_data"
    COLD_START = "cold_start"
    LIMITED_DATA = "limited_data"
    MODERATE_DATA = "moderate_data"
    SUFFICIENT_DATA = "sufficient_data"


class EvaluationFeedback(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class PersonalizationEvaluationCase(BaseModel):
    """
    One evaluation example for a student's recommendations.

    recommended_resource_ids must be ordered by recommendation rank.
    relevant_resource_ids represent the ground-truth relevant resources.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1, max_length=100)

    user_id: UUID

    recommended_resource_ids: list[str] = Field(
        default_factory=list,
        max_length=500,
    )

    relevant_resource_ids: set[str] = Field(
        default_factory=set,
        max_length=500,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    segment: EvaluationSegment

    feedback: dict[str, EvaluationFeedback] = Field(
        default_factory=dict,
    )

    baseline_resource_ids: list[str] = Field(
        default_factory=list,
        max_length=500,
    )

    @field_validator(
        "recommended_resource_ids",
        "baseline_resource_ids",
    )
    @classmethod
    def validate_unique_resource_ids(cls, value):
        normalized = [
            item.strip()
            for item in value
        ]

        if any(not item for item in normalized):
            raise ValueError(
                "Resource IDs cannot be empty."
            )

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "Resource IDs must be unique."
            )

        return normalized

    @field_validator("relevant_resource_ids")
    @classmethod
    def validate_relevant_resource_ids(cls, value):
        normalized = {
            item.strip()
            for item in value
        }

        if any(not item for item in normalized):
            raise ValueError(
                "Relevant resource IDs cannot be empty."
            )

        return normalized


class PersonalizationEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: list[PersonalizationEvaluationCase] = Field(
        min_length=1,
        max_length=10000,
    )

    k_values: list[int] = Field(
        default_factory=lambda: [3, 5, 10],
        min_length=1,
        max_length=10,
    )

    calibration_bins: int = Field(
        default=10,
        ge=2,
        le=50,
    )

    @field_validator("k_values")
    @classmethod
    def validate_k_values(cls, value):
        if any(k <= 0 for k in value):
            raise ValueError(
                "Every K value must be positive."
            )

        if len(value) != len(set(value)):
            raise ValueError(
                "K values must be unique."
            )

        return sorted(value)


class RankingMetrics(BaseModel):
    precision_at_k: float = Field(ge=0.0, le=1.0)

    recall_at_k: float = Field(ge=0.0, le=1.0)

    ndcg_at_k: float = Field(ge=0.0, le=1.0)

    reciprocal_rank: float = Field(ge=0.0, le=1.0)


class BaselineComparison(BaseModel):
    evaluated_cases: int = Field(ge=0)

    personalized_ndcg: float = Field(
        ge=0.0,
        le=1.0,
    )

    baseline_ndcg: float = Field(
        ge=0.0,
        le=1.0,
    )

    ndcg_improvement: float

    personalized_precision: float = Field(
        ge=0.0,
        le=1.0,
    )

    baseline_precision: float = Field(
        ge=0.0,
        le=1.0,
    )

    precision_improvement: float


class CalibrationMetrics(BaseModel):
    brier_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    expected_calibration_error: float = Field(
        ge=0.0,
        le=1.0,
    )

    evaluated_cases: int = Field(ge=0)


class FeedbackMetrics(BaseModel):
    total_feedback: int = Field(ge=0)

    positive_feedback: int = Field(ge=0)

    negative_feedback: int = Field(ge=0)

    neutral_feedback: int = Field(ge=0)

    positive_feedback_rate: float = Field(
        ge=0.0,
        le=1.0,
    )


class SegmentEvaluation(BaseModel):
    segment: EvaluationSegment

    evaluated_cases: int = Field(ge=0)

    average_ndcg_at_5: float = Field(
        ge=0.0,
        le=1.0,
    )

    average_precision_at_5: float = Field(
        ge=0.0,
        le=1.0,
    )

    average_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class PersonalizationEvaluationResponse(BaseModel):
    total_cases: int = Field(ge=1)

    cases_with_recommendations: int = Field(ge=0)

    recommendation_coverage: float = Field(
        ge=0.0,
        le=1.0,
    )

    ranking_metrics: dict[str, RankingMetrics]

    calibration: CalibrationMetrics

    feedback: FeedbackMetrics

    baseline_comparison: BaselineComparison | None

    segment_evaluations: list[SegmentEvaluation]

    evaluation_warnings: list[str] = Field(
        default_factory=list,
    )