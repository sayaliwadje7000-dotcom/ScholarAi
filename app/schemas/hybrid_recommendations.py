from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class HybridRecommendationRequest(BaseModel):
    """Validated request for hybrid recommendations."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="Academic query used to discover relevant resources.",
    )

    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional recommendation filters.",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional non-sensitive recommendation context.",
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of recommendations to return.",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query cannot be empty.")

        return value.strip()


class HybridComponentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    component: str
    status: str
    candidate_count: int = Field(ge=0)
    duration_ms: float = Field(ge=0)
    error_type: str | None = None
    error_message: str | None = None


class HybridComponentScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    component: str
    normalized_score: float = Field(ge=0, le=1)
    configured_weight: float = Field(ge=0, le=1)
    effective_weight: float = Field(ge=0, le=1)
    weighted_contribution: float = Field(ge=0, le=1)
    explanation: str


class HybridRecommendationExplanationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resource_id: UUID
    hybrid_score: float = Field(ge=0, le=1)
    rank: int = Field(ge=1)
    component_explanations: list[
        HybridComponentScoreResponse
    ] = Field(default_factory=list)
    summary: str


class HybridRecommendationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resource_id: UUID
    title: str
    resource_type: str
    description: str | None = None
    canonical_url: str | None = None
    hybrid_score: float = Field(ge=0, le=1)
    rank: int = Field(ge=1)
    explanation: HybridRecommendationExplanationResponse


class HybridRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: UUID
    user_id: UUID

    generated_at: datetime

    recommendations: list[
        HybridRecommendationItemResponse
    ] = Field(default_factory=list)

    component_reports: list[
        HybridComponentStatusResponse
    ] = Field(default_factory=list)

    total_candidates_discovered: int = Field(ge=0)
    total_candidates_after_deduplication: int = Field(ge=0)
    total_candidates_scored: int = Field(ge=0)
    total_candidates_accepted: int = Field(ge=0)
    total_candidates_returned: int = Field(ge=0)

    duration_ms: float = Field(ge=0)

    fallback_used: bool

    warnings: list[str] = Field(default_factory=list)


class HybridRecommendationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: str
    message: str
    request_id: UUID | None = None