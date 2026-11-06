from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


def normalize_string_list(value: Any) -> list[str]:
    """
    Normalize a metadata list.

    - Accept a list of strings.
    - Remove empty values.
    - Strip whitespace.
    - Remove duplicates case-insensitively.
    - Preserve the original capitalization of the first occurrence.
    """

    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        raise ValueError("Expected a string or list of strings.")

    normalized = []
    seen = set()

    for item in value:
        if not isinstance(item, str):
            raise ValueError(
                "All metadata list values must be strings."
            )

        item = item.strip()

        if not item:
            continue

        key = item.casefold()

        if key not in seen:
            seen.add(key)
            normalized.append(item)

    return normalized


class ResourceMetadata(BaseModel):
    """
    Standardized metadata contract for educational resources.

    Additional metadata keys are permitted to preserve compatibility
    with existing and future resource providers.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    learning_objectives: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)

    content_format: str | None = None
    source_language: str | None = None

    author: str | None = None
    provider: str | None = None

    estimated_reading_minutes: int | None = Field(
        default=None,
        ge=1,
    )

    is_beginner_friendly: bool | None = None

    last_verified_at: datetime | None = None

    @field_validator(
        "topics",
        "keywords",
        "learning_objectives",
        "prerequisites",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value):
        return normalize_string_list(value)

    @field_validator(
        "content_format",
        "source_language",
        "author",
        "provider",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value):
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError("Metadata value must be a string.")

        value = value.strip()

        return value or None


class ResourceClassification(BaseModel):
    """
    Normalized classification information used by the recommendation
    engine.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    resource_id: str

    title: str

    resource_type: str

    subject: str | None = None

    difficulty: str | None = None

    language: str | None = None

    category_slugs: list[str] = Field(default_factory=list)

    topics: list[str] = Field(default_factory=list)

    keywords: list[str] = Field(default_factory=list)

    learning_objectives: list[str] = Field(default_factory=list)

    prerequisites: list[str] = Field(default_factory=list)

    content_format: str | None = None

    estimated_duration_minutes: int | None = Field(
        default=None,
        ge=1,
    )

    estimated_reading_minutes: int | None = Field(
        default=None,
        ge=1,
    )

    is_beginner_friendly: bool | None = None

    quality_score: float | None = Field(
        default=None,
        ge=0,
        le=5,
    )

    # Phase 10.7: Resource eligibility
    is_active: bool = True

    published_at: datetime | None = None

    last_verified_at: datetime | None = None

    @field_validator(
        "category_slugs",
        "topics",
        "keywords",
        "learning_objectives",
        "prerequisites",
        mode="before",
    )
    @classmethod
    def normalize_classification_lists(cls, value):
        return normalize_string_list(value)