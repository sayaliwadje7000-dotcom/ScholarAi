from datetime import datetime, timezone
from typing import Any

from app.schemas.recommendations import (
    InteractionSummary,
    LearningContext,
    RecommendationRequest,
)

from app.schemas.recommendation_context import (
    RecommendationContext,
    RecommendationIntent,
    normalize_string_list,
)


class LearningContextBuilder:
    """
    Builds a normalized recommendation context from:

    - Existing user information
    - User preferences
    - Recent resource interactions
    - Current recommendation request

    This service does not query the database.
    """

    def __init__(
        self,
        max_recent_interactions: int = 20,
    ):
        if (
            isinstance(max_recent_interactions, bool)
            or not isinstance(max_recent_interactions, int)
            or max_recent_interactions < 1
        ):
            raise ValueError(
                "max_recent_interactions must be a positive integer."
            )

        self.max_recent_interactions = max_recent_interactions

    @staticmethod
    def _get_attribute(
        obj: Any,
        attribute: str,
        default=None,
    ):
        if obj is None:
            return default

        if isinstance(obj, dict):
            return obj.get(attribute, default)

        return getattr(obj, attribute, default)

    @staticmethod
    def _normalize_optional_string(value):
        if value is None:
            return None

        if not isinstance(value, str):
            return None

        value = value.strip()

        return value or None

    @staticmethod
    def _normalize_language(value):
        value = LearningContextBuilder._normalize_optional_string(
            value
        )

        return value.lower() if value else None

    @staticmethod
    def _interaction_timestamp(interaction):
        """
        Produce a sortable timestamp.

        Missing timestamps sort before dated interactions.
        Naive datetimes are interpreted as UTC.
        """

        occurred_at = LearningContextBuilder._get_attribute(
            interaction,
            "occurred_at",
        )

        if not isinstance(occurred_at, datetime):
            return float("-inf")

        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(
                tzinfo=timezone.utc
            )

        return occurred_at.timestamp()

    def _normalize_interactions(
        self,
        interactions,
    ) -> list[InteractionSummary]:
        """
        Convert interaction records into validated summaries.

        Most recent interactions are retained.
        """

        if interactions is None:
            return []

        valid_interactions = []

        for interaction in interactions:
            interaction_data = {
                "resource_id": self._get_attribute(
                    interaction,
                    "resource_id",
                ),
                "interaction_type": self._get_attribute(
                    interaction,
                    "interaction_type",
                ),
                "rating": self._get_attribute(
                    interaction,
                    "rating",
                ),
                "duration_seconds": self._get_attribute(
                    interaction,
                    "duration_seconds",
                    0,
                ),
                "occurred_at": self._get_attribute(
                    interaction,
                    "occurred_at",
                ),
            }

            if interaction_data["resource_id"] is None:
                continue

            try:
                summary = InteractionSummary.model_validate(
                    interaction_data
                )

            except (ValueError, TypeError):
                continue

            valid_interactions.append(
                (
                    self._interaction_timestamp(interaction),
                    summary,
                )
            )

        valid_interactions.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            summary
            for _, summary in valid_interactions[
                :self.max_recent_interactions
            ]
        ]

    def _build_intent(
        self,
        request: RecommendationRequest | None,
    ) -> RecommendationIntent:
        if request is None:
            return RecommendationIntent()

        return RecommendationIntent(
            query=request.query,
            subject=request.subject,
            resource_types=request.resource_types,
            difficulty_level=request.difficulty_level,
            language=request.language,
            recommendation_type=request.recommendation_type,
            exclude_completed=request.exclude_completed,
        )

    def build(
        self,
        user,
        request: RecommendationRequest | None = None,
        interactions=None,
    ) -> RecommendationContext:
        """
        Build the complete recommendation context.

        Explicit request values take precedence over stored preferences
        where both represent the same preference.

        The original user, preferences and interaction records are
        never modified.
        """

        if user is None:
            raise ValueError(
                "An authenticated user is required."
            )

        user_id = self._get_attribute(user, "id")

        if user_id is None:
            raise ValueError(
                "User ID is required."
            )

        preferences = self._get_attribute(
            user,
            "preferences",
        )

        preferred_language = self._normalize_language(
            self._get_attribute(
                preferences,
                "preferred_language",
            )
        )

        preferred_subjects = normalize_string_list(
            self._get_attribute(
                preferences,
                "preferred_subjects",
                [],
            )
        )

        learning_goals = normalize_string_list(
            self._get_attribute(
                preferences,
                "learning_goals",
                [],
            )
        )

        education_level = self._normalize_optional_string(
            self._get_attribute(
                preferences,
                "education_level",
            )
        )

        if request is not None:
            if request.language:
                preferred_language = request.language.lower()

            if request.subject:
                preferred_subjects = normalize_string_list(
                    [
                        request.subject,
                        *preferred_subjects,
                    ]
                )

        if interactions is None:
            interactions = self._get_attribute(
                user,
                "resource_interactions",
                [],
            )

        recent_interactions = self._normalize_interactions(
            interactions
        )

        learning_context = LearningContext(
            user_id=user_id,
            preferred_language=preferred_language,
            education_level=education_level,
            preferred_subjects=preferred_subjects,
            learning_goals=learning_goals,
            recent_interactions=recent_interactions,
        )

        intent = self._build_intent(request)

        return RecommendationContext(
            learning_context=learning_context,
            intent=intent,
        )