"""Typed feature contracts for ScholarAI recommendation ML."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


FEATURE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class RecommendationFeatureRow:
    """
    One feature row for a user-resource recommendation pair.

    Identifiers are retained for grouping and auditing.
    They are never included as model features.
    """

    user_id: UUID
    resource_id: UUID

    prediction_at: datetime

    # User features
    preferred_language: str | None
    education_level: str | None
    preferred_subjects: tuple[str, ...]
    learning_goals: tuple[str, ...]

    # Resource features
    resource_type: str
    subject: str | None
    language: str | None
    difficulty_level: str | None
    provider: str | None

    categories: tuple[str, ...]

    # Resource content
    title: str
    description: str
    topics: tuple[str, ...]
    keywords: tuple[str, ...]
    learning_objectives: tuple[str, ...]
    prerequisites: tuple[str, ...]

    # Numerical resource features
    quality_score: float | None
    estimated_duration_minutes: float | None
    resource_age_days: float | None

    # Historical user activity
    historical_view_count: int
    historical_click_count: int
    historical_save_count: int
    historical_completion_count: int
    historical_rating_count: int
    historical_average_rating: float | None

    # Semantic features
    resource_embedding: tuple[float, ...] | None = None

    schema_version: str = FEATURE_SCHEMA_VERSION

    def __post_init__(self) -> None:

        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")

        if not isinstance(self.resource_id, UUID):
            raise TypeError("resource_id must be UUID")

        if (
            self.prediction_at.tzinfo is None
            or self.prediction_at.utcoffset() is None
        ):
            raise ValueError(
                "prediction_at must be timezone-aware"
            )

        if not self.title.strip():
            raise ValueError("title cannot be empty")

        if not self.resource_type.strip():
            raise ValueError(
                "resource_type cannot be empty"
            )

        if self.schema_version != FEATURE_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported feature schema version"
            )

        numerical_counts = (
            self.historical_view_count,
            self.historical_click_count,
            self.historical_save_count,
            self.historical_completion_count,
            self.historical_rating_count,
        )

        if any(value < 0 for value in numerical_counts):
            raise ValueError(
                "Historical counts cannot be negative"
            )

        if self.quality_score is not None:
            if not 0 <= self.quality_score <= 5:
                raise ValueError(
                    "quality_score must be between 0 and 5"
                )

        if (
            self.estimated_duration_minutes is not None
            and self.estimated_duration_minutes < 0
        ):
            raise ValueError(
                "Duration cannot be negative"
            )

        if (
            self.resource_age_days is not None
            and self.resource_age_days < 0
        ):
            raise ValueError(
                "Resource age cannot be negative"
            )

        if self.historical_average_rating is not None:
            if not 1 <= self.historical_average_rating <= 5:
                raise ValueError(
                    "Average rating must be between 1 and 5"
                )

        if self.resource_embedding is not None:

            if not self.resource_embedding:
                raise ValueError(
                    "Resource embedding cannot be empty"
                )

            for value in self.resource_embedding:

                if not isinstance(value, (int, float)):
                    raise TypeError(
                        "Embedding values must be numerical"
                    )

                if not __import__("math").isfinite(value):
                    raise ValueError(
                        "Embedding values must be finite"
                    )

    @property
    def grouping_key(self) -> tuple[UUID, UUID]:
        return self.user_id, self.resource_id

    def to_model_features(self) -> dict[str, Any]:
        """
        Produce model-facing features.

        Direct identifiers and prediction timestamps are excluded.
        """

        return {
            "preferred_language": self.preferred_language,
            "education_level": self.education_level,
            "preferred_subjects": list(
                self.preferred_subjects
            ),
            "learning_goals": list(
                self.learning_goals
            ),
            "resource_type": self.resource_type,
            "subject": self.subject,
            "language": self.language,
            "difficulty_level": self.difficulty_level,
            "provider": self.provider,
            "categories": list(self.categories),
            "title": self.title,
            "description": self.description,
            "topics": list(self.topics),
            "keywords": list(self.keywords),
            "learning_objectives": list(
                self.learning_objectives
            ),
            "prerequisites": list(
                self.prerequisites
            ),
            "quality_score": self.quality_score,
            "estimated_duration_minutes": (
                self.estimated_duration_minutes
            ),
            "resource_age_days": self.resource_age_days,
            "historical_view_count": (
                self.historical_view_count
            ),
            "historical_click_count": (
                self.historical_click_count
            ),
            "historical_save_count": (
                self.historical_save_count
            ),
            "historical_completion_count": (
                self.historical_completion_count
            ),
            "historical_rating_count": (
                self.historical_rating_count
            ),
            "historical_average_rating": (
                self.historical_average_rating
            ),
            "resource_embedding": (
                list(self.resource_embedding)
                if self.resource_embedding is not None
                else None
            ),
        }