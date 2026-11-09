from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# ENUMS
# ============================================================


class LearningGoalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LearningGoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


# ============================================================
# COMMON NORMALIZATION
# ============================================================


def normalize_string_list(value):

    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        raise ValueError(
            "Expected a string or list of strings."
        )

    normalized = []
    seen = set()

    for item in value:

        if not isinstance(item, str):
            raise ValueError(
                "All list values must be strings."
            )

        item = item.strip()

        if not item:
            continue

        key = item.casefold()

        if key not in seen:
            seen.add(key)
            normalized.append(item)

    return normalized


# ============================================================
# LEARNING GOAL
# ============================================================


class LearningGoalBase(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(
        min_length=3,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    subject: str | None = Field(
        default=None,
        max_length=150,
    )

    priority: LearningGoalPriority = (
        LearningGoalPriority.MEDIUM
    )

    status: LearningGoalStatus = (
        LearningGoalStatus.ACTIVE
    )

    target_date: datetime | None = None

    progress_percent: int = Field(
        default=0,
        ge=0,
        le=100,
    )

    @field_validator(
        "title",
        "description",
        "subject",
    )
    @classmethod
    def normalize_text(cls, value):

        if value is None:
            return None

        value = value.strip()

        return value or None

    @model_validator(mode="after")
    def validate_goal_completion(self):

        if self.status == LearningGoalStatus.COMPLETED:

            if self.progress_percent != 100:
                self.progress_percent = 100

        elif self.progress_percent == 100:

            self.status = LearningGoalStatus.COMPLETED

        return self


class LearningGoalCreate(LearningGoalBase):
    """
    Request schema for creating a learning goal.
    """

    pass


class LearningGoalUpdate(BaseModel):
    """
    Partial update schema for learning goals.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    subject: str | None = Field(
        default=None,
        max_length=150,
    )

    priority: LearningGoalPriority | None = None

    status: LearningGoalStatus | None = None

    target_date: datetime | None = None

    progress_percent: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    @field_validator(
        "title",
        "description",
        "subject",
    )
    @classmethod
    def normalize_text(cls, value):

        if value is None:
            return None

        value = value.strip()

        return value or None


class LearningGoalResponse(LearningGoalBase):
    """
    Learning goal returned by the API.
    """

    id: UUID

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


# ============================================================
# LEARNING PROFILE
# ============================================================


class LearningProfileUpdate(BaseModel):
    """
    Partial update of an existing user learning profile.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    preferred_language: str | None = Field(
        default=None,
        max_length=10,
    )

    education_level: str | None = Field(
        default=None,
        max_length=50,
    )

    preferred_subjects: list[str] | None = Field(
        default=None,
        max_length=50,
    )

    notification_enabled: bool | None = None

    @field_validator(
        "preferred_language",
        "education_level",
    )
    @classmethod
    def normalize_optional_text(cls, value):

        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("preferred_subjects")
    @classmethod
    def normalize_subjects(cls, value):

        if value is None:
            return None

        return normalize_string_list(value)


class LearningProfileResponse(BaseModel):
    """
    Complete learning profile returned to the student.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    user_id: UUID

    preferred_language: str | None = None

    education_level: str | None = None

    preferred_subjects: list[str] = Field(
        default_factory=list,
    )

    notification_enabled: bool = True

    learning_goals: list[LearningGoalResponse] = Field(
        default_factory=list,
    )

    created_at: datetime

    updated_at: datetime