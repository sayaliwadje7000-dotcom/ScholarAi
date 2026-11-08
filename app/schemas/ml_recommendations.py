from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MLRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_ids: list[UUID] = Field(
        min_length=1,
        max_length=100,
        description="Candidate study resource identifiers.",
    )

    prediction_at: datetime | None = Field(
        default=None,
        description=(
            "Optional timezone-aware prediction timestamp. "
            "Defaults to the current UTC time."
        ),
    )


class MLRecommendationItem(BaseModel):
    resource_id: UUID

    relevance_probability: float = Field(
        ge=0.0,
        le=1.0,
    )

    is_relevant: bool


class MLRecommendationResponse(BaseModel):
    user_id: UUID

    model_run_id: str

    total_results: int

    recommendations: list[MLRecommendationItem]

    generated_at: datetime