from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ExplanationFactor(BaseModel):
    """
    Represents one factor contributing to a recommendation score.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    factor: str = Field(
        min_length=1,
        max_length=100,
    )

    score: float = Field(
        ge=0.0,
        le=1.0,
    )

    weight: float = Field(
        ge=0.0,
        le=1.0,
    )

    weighted_contribution: float = Field(
        ge=0.0,
        le=1.0,
    )

    description: str = Field(
        min_length=1,
        max_length=300,
    )


class RecommendationExplanation(BaseModel):
    """
    Structured explanation for a ranked recommendation.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    resource_id: UUID

    rank_position: int = Field(
        ge=1,
    )

    recommendation_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    reason: str = Field(
        min_length=1,
        max_length=500,
    )

    highlights: list[str] = Field(
        default_factory=list,
        max_length=3,
    )

    factors: list[ExplanationFactor] = Field(
        default_factory=list,
        max_length=6,
    )

    algorithm_version: str = Field(
        min_length=1,
        max_length=50,
    )

    explanation_version: str = Field(
        default="v1",
        min_length=1,
        max_length=50,
    )