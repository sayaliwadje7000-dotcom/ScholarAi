from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas.recommendation_explanation import (
    RecommendationExplanation,
)


class RecommendedResourceAPIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    title: str

    description: str | None = None

    resource_type: str

    url: str

    provider: str | None = None

    subject: str | None = None

    language: str | None = None

    difficulty_level: str | None = None

    estimated_duration_minutes: int | None = None

    quality_score: float | None = None


class RecommendationItemAPIResponse(BaseModel):
    recommendation_id: UUID

    resource: RecommendedResourceAPIResponse

    explanation: RecommendationExplanation

    status: str

    generated_at: datetime


class RecommendationGenerationAPIResponse(BaseModel):
    request_id: UUID

    total_results: int

    recommendations: list[RecommendationItemAPIResponse]

    generated_at: datetime

    algorithm_version: str


class RecommendationHistoryAPIResponse(BaseModel):
    total_results: int

    recommendations: list[RecommendationItemAPIResponse]


from pydantic import field_validator


class RecommendationFeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_type: str

    comment: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, value):
        allowed = {
            "helpful",
            "not_helpful",
            "irrelevant",
        }

        if value not in allowed:
            raise ValueError("Invalid feedback type.")

        return value.strip()

        


class RecommendationFeedbackAPIResponse(BaseModel):
    id: UUID

    recommendation_id: UUID

    feedback_type: str

    comment: str | None = None

    created_at: datetime