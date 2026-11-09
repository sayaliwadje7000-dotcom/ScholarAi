from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdaptationMode(str, Enum):
    COLD_START = "cold_start"
    PROFILE_GUIDED = "profile_guided"
    BEHAVIOR_GUIDED = "behavior_guided"
    FEEDBACK_GUIDED = "feedback_guided"
    FULL_PERSONALIZATION = "full_personalization"


class AdaptationReason(str, Enum):
    ACTIVE_LEARNING_GOALS = "active_learning_goals"
    EXPLICIT_SUBJECT_PREFERENCES = "explicit_subject_preferences"
    BEHAVIORAL_EVIDENCE = "behavioral_evidence"
    EXPLICIT_FEEDBACK = "explicit_feedback"
    SPARSE_EVIDENCE = "sparse_evidence"
    INSUFFICIENT_PERSONALIZATION_DATA = (
        "insufficient_personalization_data"
    )


class AdaptiveRecommendationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: AdaptationMode
    profile_weight: float = Field(ge=0.0, le=1.0)
    behavioral_weight: float = Field(ge=0.0, le=1.0)
    feedback_weight: float = Field(ge=0.0, le=1.0)
    evidence_confidence: float = Field(ge=0.0, le=1.0)
    reasons: tuple[AdaptationReason, ...] = ()


class AdaptiveRecommendationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: UUID
    recommendations: Any
    personalization_context: Any
    policy: AdaptiveRecommendationPolicy
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    adaptation_applied: bool
    warnings: tuple[str, ...] = ()