"""Extract recommendation ML features from ScholarAI domain models."""

from __future__ import annotations

import math

from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from app.models.study_resource import StudyResource
from app.models.user_preferences import UserPreferences
from app.models.user_resource_interaction import (
    UserResourceInteraction,
)

from app.services.recommendations.ml.features.feature_schema import (
    RecommendationFeatureRow,
)


class RecommendationFeatureExtractionError(Exception):
    """Raised when recommendation feature extraction fails."""


class RecommendationFeatureExtractor:
    """
    Extracts user, resource and historical interaction features.

    Database access is intentionally excluded.
    The caller supplies already-loaded domain objects.
    """

    INTERACTION_TYPES = {
        "view",
        "click",
        "save",
        "complete",
        "rate",
    }

    METADATA_FEATURES = (
        "topics",
        "keywords",
        "learning_objectives",
        "prerequisites",
    )

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:

        if value is None:
            return None

        if not isinstance(value, str):
            raise RecommendationFeatureExtractionError(
                "Expected a textual feature"
            )

        normalized = " ".join(value.split()).casefold()

        return normalized or None

    @classmethod
    def _normalize_terms(
        cls,
        values: Any,
    ) -> tuple[str, ...]:

        if values is None:
            return ()

        if isinstance(values, str):
            values = [values]

        if not isinstance(values, (list, tuple, set)):
            raise RecommendationFeatureExtractionError(
                "Expected a list of textual features"
            )

        normalized = []

        seen = set()

        for value in values:

            if not isinstance(value, str):
                continue

            item = " ".join(value.split()).casefold()

            if item and item not in seen:
                seen.add(item)
                normalized.append(item)

        return tuple(normalized)

    @staticmethod
    def _validate_prediction_time(
        prediction_at: datetime,
    ) -> datetime:

        if (
            prediction_at.tzinfo is None
            or prediction_at.utcoffset() is None
        ):
            raise RecommendationFeatureExtractionError(
                "Prediction time must be timezone-aware"
            )

        return prediction_at.astimezone(timezone.utc)

    @staticmethod
    def _safe_float(value: Any) -> float | None:

        if value is None:
            return None

        try:
            result = float(value)

        except (TypeError, ValueError):
            return None

        if not math.isfinite(result):
            return None

        return result

    @staticmethod
    def _resource_metadata(
        resource: StudyResource,
    ) -> dict:

        metadata = resource.resource_metadata or {}

        if not isinstance(metadata, dict):
            return {}

        return metadata

    def _extract_categories(
        self,
        resource: StudyResource,
    ) -> tuple[str, ...]:

        categories = []

        for category in resource.categories or []:

            if not getattr(category, "is_active", True):
                continue

            slug = getattr(category, "slug", None)

            if isinstance(slug, str) and slug.strip():
                categories.append(slug)

        return self._normalize_terms(categories)

    def _extract_content_metadata(
        self,
        resource: StudyResource,
    ) -> dict[str, tuple[str, ...]]:

        metadata = self._resource_metadata(resource)

        result = {}

        for field in self.METADATA_FEATURES:

            result[field] = self._normalize_terms(
                metadata.get(field)
            )

        return result

    @staticmethod
    def _extract_embedding(
        resource_embedding: Any,
    ) -> tuple[float, ...] | None:

        if resource_embedding is None:
            return None

        if getattr(resource_embedding, "status", None) != "ready":
            return None

        vector = getattr(
            resource_embedding,
            "embedding",
            None,
        )

        if vector is None:
            return None

        try:
            values = tuple(float(value) for value in vector)

        except (TypeError, ValueError):
            raise RecommendationFeatureExtractionError(
                "Invalid resource embedding"
            )

        if not values:
            return None

        if not all(math.isfinite(value) for value in values):
            raise RecommendationFeatureExtractionError(
                "Embedding contains non-finite values"
            )

        return values

    def _extract_history(
        self,
        interactions: Iterable[UserResourceInteraction],
        user_id: UUID,
        target_resource_id: UUID,
        prediction_at: datetime,
    ) -> dict:

        counts = {
            "view": 0,
            "click": 0,
            "save": 0,
            "complete": 0,
            "rate": 0,
        }

        ratings = []

        for interaction in interactions:

            if interaction.user_id != user_id:
                continue

            # Exclude the target resource to prevent
            # target-specific interaction leakage.
            if interaction.resource_id == target_resource_id:
                continue

            occurred_at = interaction.occurred_at

            if occurred_at is None:
                continue

            if (
                occurred_at.tzinfo is None
                or occurred_at.utcoffset() is None
            ):
                raise RecommendationFeatureExtractionError(
                    "Interaction timestamp must be timezone-aware"
                )

            occurred_at = occurred_at.astimezone(timezone.utc)

            # Only events available before prediction time.
            if occurred_at >= prediction_at:
                continue

            event_type = interaction.interaction_type

            if event_type not in self.INTERACTION_TYPES:
                continue

            counts[event_type] += 1

            if event_type == "rate":

                rating = interaction.rating

                if rating is not None and 1 <= rating <= 5:
                    ratings.append(float(rating))

        return {
            "historical_view_count": counts["view"],
            "historical_click_count": counts["click"],
            "historical_save_count": counts["save"],
            "historical_completion_count": counts["complete"],
            "historical_rating_count": counts["rate"],
            "historical_average_rating": (
                sum(ratings) / len(ratings)
                if ratings
                else None
            ),
        }

    def extract(
        self,
        *,
        user_id: UUID,
        resource: StudyResource,
        preferences: UserPreferences | None,
        interactions: Iterable[UserResourceInteraction],
        prediction_at: datetime,
        resource_embedding: Any = None,
    ) -> RecommendationFeatureRow:
        """
        Build one feature row for a user-resource pair.

        The caller is responsible for loading the relevant ORM
        objects and supplying a historical interaction set.
        """

        try:

            prediction_at = self._validate_prediction_time(
                prediction_at
            )

            if not isinstance(resource, StudyResource):
                raise RecommendationFeatureExtractionError(
                    "resource must be a StudyResource instance"
                )

            if not isinstance(resource.id, UUID):
                raise RecommendationFeatureExtractionError(
                    "Resource must have a valid UUID"
                )

            if not isinstance(user_id, UUID):
                raise RecommendationFeatureExtractionError(
                    "user_id must be a UUID"
                )

            if not resource.title or not resource.title.strip():
                raise RecommendationFeatureExtractionError(
                    "Resource title is required"
                )

            if not resource.resource_type:
                raise RecommendationFeatureExtractionError(
                    "Resource type is required"
                )

            metadata = self._extract_content_metadata(resource)

            categories = self._extract_categories(resource)

            history = self._extract_history(
                interactions=interactions,
                user_id=user_id,
                target_resource_id=resource.id,
                prediction_at=prediction_at,
            )

            resource_age_days = None

            if resource.published_at is not None:

                published_at = resource.published_at

                if (
                    published_at.tzinfo is None
                    or published_at.utcoffset() is None
                ):
                    raise RecommendationFeatureExtractionError(
                        "Resource publication timestamp must be timezone-aware"
                    )

                age = prediction_at - published_at.astimezone(
                    timezone.utc
                )

                if age.total_seconds() < 0:
                    resource_age_days = 0.0

                else:
                    resource_age_days = (
                        age.total_seconds() / 86400
                    )

            return RecommendationFeatureRow(

                user_id=user_id,

                resource_id=resource.id,

                prediction_at=prediction_at,

                preferred_language=(
                    self._normalize_optional_text(
                        preferences.preferred_language
                    )
                    if preferences
                    else None
                ),

                education_level=(
                    self._normalize_optional_text(
                        preferences.education_level
                    )
                    if preferences
                    else None
                ),

                preferred_subjects=(
                    self._normalize_terms(
                        preferences.preferred_subjects
                    )
                    if preferences
                    else ()
                ),

                learning_goals=(
                    self._normalize_terms(
                        preferences.learning_goals
                    )
                    if preferences
                    else ()
                ),

                resource_type=(
                    self._normalize_optional_text(
                        resource.resource_type
                    )
                    or "unknown"
                ),

                subject=self._normalize_optional_text(
                    resource.subject
                ),

                language=self._normalize_optional_text(
                    resource.language
                ),

                difficulty_level=self._normalize_optional_text(
                    resource.difficulty_level
                ),

                provider=self._normalize_optional_text(
                    resource.provider
                ),

                categories=categories,

                title=resource.title.strip(),

                description=resource.description or "",

                topics=metadata["topics"],

                keywords=metadata["keywords"],

                learning_objectives=metadata[
                    "learning_objectives"
                ],

                prerequisites=metadata["prerequisites"],

                quality_score=self._safe_float(
                    resource.quality_score
                ),

                estimated_duration_minutes=self._safe_float(
                    resource.estimated_duration_minutes
                ),

                resource_age_days=resource_age_days,

                historical_view_count=history[
                    "historical_view_count"
                ],

                historical_click_count=history[
                    "historical_click_count"
                ],

                historical_save_count=history[
                    "historical_save_count"
                ],

                historical_completion_count=history[
                    "historical_completion_count"
                ],

                historical_rating_count=history[
                    "historical_rating_count"
                ],

                historical_average_rating=history[
                    "historical_average_rating"
                ],

                resource_embedding=self._extract_embedding(
                    resource_embedding
                ),
            )

        except RecommendationFeatureExtractionError:
            raise

        except Exception as exc:

            raise RecommendationFeatureExtractionError(
                "Failed to extract recommendation features"
            ) from exc