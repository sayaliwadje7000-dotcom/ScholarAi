from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SparseDataLevel(str, Enum):
    NO_DATA = "no_data"
    COLD_START = "cold_start"
    LIMITED_DATA = "limited_data"
    MODERATE_DATA = "moderate_data"
    SUFFICIENT_DATA = "sufficient_data"


class SparseDataReason(str, Enum):
    NO_PROFILE = "no_profile"
    NO_BEHAVIORAL_HISTORY = "no_behavioral_history"
    NO_EXPLICIT_FEEDBACK = "no_explicit_feedback"
    LOW_EVIDENCE_COUNT = "low_evidence_count"
    LOW_CONFIDENCE = "low_confidence"
    PROFILE_AVAILABLE = "profile_available"
    BEHAVIORAL_HISTORY_AVAILABLE = "behavioral_history_available"
    FEEDBACK_AVAILABLE = "feedback_available"
    SUFFICIENT_EVIDENCE = "sufficient_evidence"


class ColdStartStrategy(str, Enum):
    GENERAL_DISCOVERY = "general_discovery"
    PROFILE_GUIDED_DISCOVERY = "profile_guided_discovery"
    LIMITED_PERSONALIZATION = "limited_personalization"
    BEHAVIOR_GUIDED_PERSONALIZATION = (
        "behavior_guided_personalization"
    )
    FULL_PERSONALIZATION = "full_personalization"


class SparseEvidenceSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_available: bool

    preferred_subject_count: int = Field(ge=0)
    learning_goal_count: int = Field(ge=0)

    behavioral_signal_count: int = Field(ge=0)
    positive_signal_count: int = Field(ge=0)
    negative_signal_count: int = Field(ge=0)
    neutral_signal_count: int = Field(ge=0)

    feedback_count: int = Field(ge=0)
    positive_feedback_count: int = Field(ge=0)
    negative_feedback_count: int = Field(ge=0)

    evidence_count: int = Field(ge=0)

    profile_confidence: float = Field(ge=0.0, le=1.0)
    behavioral_confidence: float = Field(ge=0.0, le=1.0)
    feedback_confidence: float = Field(ge=0.0, le=1.0)
    overall_confidence: float = Field(ge=0.0, le=1.0)


class ColdStartPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: ColdStartStrategy
    exploration_ratio: float = Field(ge=0.0, le=1.0)
    personalization_strength: float = Field(
        ge=0.0,
        le=1.0,
    )

    use_explicit_preferences: bool
    use_behavioral_signals: bool
    use_explicit_feedback: bool

    use_general_fallback: bool
    preserve_hard_constraints: bool = True
    treat_missing_evidence_as_neutral: bool = True

    reasons: tuple[SparseDataReason, ...] = ()


class SparseDataAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_level: SparseDataLevel

    evidence: SparseEvidenceSummary
    policy: ColdStartPolicy

    is_cold_start: bool
    is_sparse: bool

    warnings: tuple[str, ...] = ()

    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )