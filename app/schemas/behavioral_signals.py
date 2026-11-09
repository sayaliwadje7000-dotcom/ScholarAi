from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# LEARNING ACTIVITY TYPES
# ============================================================


class LearningActivityType(str, Enum):

    DOCUMENT_UPLOADED = "document_uploaded"

    STUDY_SESSION_STARTED = "study_session_started"

    STUDY_SESSION_COMPLETED = "study_session_completed"

    AI_QUESTION_ASKED = "ai_question_asked"

    QUIZ_ATTEMPTED = "quiz_attempted"

    QUIZ_COMPLETED = "quiz_completed"

    SEARCH_PERFORMED = "search_performed"

    RESOURCE_RECOMMENDED = "resource_recommended"


# ============================================================
# SIGNAL SOURCE
# ============================================================


class BehavioralSignalSource(str, Enum):

     LEARNING_ACTIVITY = "learning_activity"
     RESOURCE_INTERACTION = "resource_interaction"
     RECOMMENDATION_FEEDBACK = "recommendation_feedback"


# ============================================================
# LEARNING ACTIVITY REQUEST
# ============================================================


class LearningActivityCreate(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    activity_type: LearningActivityType

    entity_type: str | None = Field(
        default=None,
        max_length=50,
    )

    entity_id: UUID | None = None

    duration_seconds: int | None = Field(
        default=None,
        ge=0,
    )

    activity_metadata: dict = Field(
        default_factory=dict,
    )

    @field_validator("entity_type")
    @classmethod
    def normalize_entity_type(cls, value):

        if value is None:
            return None

        value = value.strip().lower()

        return value or None

    @model_validator(mode="after")
    def validate_entity_reference(self):

        if (
            self.entity_type is None
            and self.entity_id is not None
        ):
            raise ValueError(
                "entity_type is required when entity_id is provided."
            )

        if (
            self.entity_type is not None
            and self.entity_id is None
        ):
            raise ValueError(
                "entity_id is required when entity_type is provided."
            )

        return self

    @field_validator("activity_metadata")
    @classmethod
    def validate_metadata(cls, value):

        if not isinstance(value, dict):
            raise ValueError(
                "Activity metadata must be an object."
            )

        return value


# ============================================================
# LEARNING ACTIVITY RESPONSE
# ============================================================


class LearningActivityResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    activity_type: str

    entity_type: str | None

    entity_id: UUID | None

    duration_seconds: int | None

    occurred_at: datetime


# ============================================================
# NORMALIZED BEHAVIORAL SIGNAL
# ============================================================


class BehavioralSignal(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
    )

    source: BehavioralSignalSource

    source_event_id: UUID

    event_type: str

    entity_type: str | None = None

    entity_id: UUID | None = None

    resource_id: UUID | None = None

    signal_strength: float = Field(
        ge=-1.0,
        le=1.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    duration_seconds: int | None = Field(
        default=None,
        ge=0,
    )

    occurred_at: datetime

    metadata: dict = Field(
        default_factory=dict,
    )


# ============================================================
# SIGNAL COLLECTION RESPONSE
# ============================================================


class BehavioralSignalCollection(BaseModel):

    user_id: UUID

    total_signals: int

    activity_signals: int

    interaction_signals: int

    signals: list[BehavioralSignal]

    generated_at: datetime