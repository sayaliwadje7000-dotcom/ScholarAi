from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.recommendations import (
    DifficultyLevel,
    LearningContext,
    RecommendationType,
    ResourceType,
)


def normalize_string_list(value):
    """
    Normalize a list of strings.

    Removes whitespace, empty values and case-insensitive duplicates.
    Preserves the capitalization of the first occurrence.
    """

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
                "All values must be strings."
            )

        item = item.strip()

        if not item:
            continue

        key = item.casefold()

        if key not in seen:
            seen.add(key)
            normalized.append(item)

    return normalized


class RecommendationIntent(BaseModel):
    """
    Represents the student's immediate recommendation intent.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str | None = Field(
        default=None,
        max_length=1000,
    )

    subject: str | None = Field(
        default=None,
        max_length=150,
    )

    resource_types: list[ResourceType] = Field(
        default_factory=list,
    )

    difficulty_level: DifficultyLevel | None = None

    language: str | None = Field(
        default=None,
        max_length=20,
    )

    recommendation_type: RecommendationType = (
        RecommendationType.PERSONALIZED
    )

    exclude_completed: bool = True

    @field_validator(
        "query",
        "subject",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                "Expected a string."
            )

        value = value.strip()

        return value or None

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value):
        if value is None:
            return None

        return value.strip().lower()

    @field_validator("resource_types")
    @classmethod
    def remove_duplicate_resource_types(cls, value):
        return list(dict.fromkeys(value))


class RecommendationContext(BaseModel):
    """
    Complete context supplied to the recommendation engine.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    learning_context: LearningContext

    intent: RecommendationIntent

    context_version: str = "v1"


# Explicitly rebuild the model after its dependencies are imported.
RecommendationContext.model_rebuild()