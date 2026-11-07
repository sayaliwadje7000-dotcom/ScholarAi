from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContentRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=2,
        max_length=2000,
    )

    subject: str | None = Field(
        default=None,
        max_length=100,
    )

    language: str | None = Field(
        default=None,
        max_length=30,
    )

    difficulty_level: str | None = Field(
        default=None,
        max_length=30,
    )

    resource_types: list[str] = Field(
        default_factory=list,
        max_length=8,
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    minimum_similarity: float = Field(
        default=0.30,
        ge=-1.0,
        le=1.0,
    )

    exclude_completed: bool = True


class ContentRecommendationItem(BaseModel):
    resource_id: UUID
    title: str
    description: str | None = None
    resource_type: str
    subject: str | None = None
    language: str | None = None
    difficulty_level: str | None = None
    url: str | None = None

    similarity_score: float = Field(
        ge=-1.0,
        le=1.0,
    )

    content_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    matched_topics: list[str] = Field(
        default_factory=list,
    )

    matched_keywords: list[str] = Field(
        default_factory=list,
    )

    matched_objectives: list[str] = Field(
        default_factory=list,
    )

    explanation: str


class ContentRecommendationResponse(BaseModel):
    query: str

    total_results: int

    recommendations: list[ContentRecommendationItem]

    algorithm_version: str

    status: str = "success"