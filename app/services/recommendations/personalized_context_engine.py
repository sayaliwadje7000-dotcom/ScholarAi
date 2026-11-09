from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.schemas.personalized_learning_context import (
    BehavioralEvidenceSummary,
    FeedbackEvidenceSummary,
    LearningGoalContext,
    PersonalizedLearningContext,
    PersonalizationConfidence,
)

from app.services.recommendations.context_builder import (
    LearningContextBuilder,
)


class PersonalizedContextEngine:
    """
    Builds a unified personalization context from existing
    profile, behavioral and recommendation-feedback data.

    This service is deliberately independent of database
    sessions and recommendation scoring implementations.
    """

    DEFAULT_RECENT_INTERACTIONS = 20

    MIN_EVIDENCE_FOR_DENSE_PROFILE = 5

    def __init__(
        self,
        context_builder: LearningContextBuilder | None = None,
        sparse_evidence_threshold: int = 5,
    ) -> None:

        if (
            isinstance(sparse_evidence_threshold, bool)
            or not isinstance(sparse_evidence_threshold, int)
            or sparse_evidence_threshold < 1
        ):
            raise ValueError(
                "sparse_evidence_threshold must be a positive integer"
            )

        self.context_builder = (
            context_builder or LearningContextBuilder()
        )

        self.sparse_evidence_threshold = (
            sparse_evidence_threshold
        )

    @staticmethod
    def _get(value: Any, key: str, default=None):
        if value is None:
            return default

        if isinstance(value, dict):
            return value.get(key, default)

        return getattr(value, key, default)

    @staticmethod
    def _normalize_datetime(
        value: datetime | None,
    ) -> datetime | None:

        if value is None:
            return None

        if not isinstance(value, datetime):
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    @staticmethod
    def _normalize_text(value: Any) -> str | None:

        if not isinstance(value, str):
            return None

        value = value.strip()

        return value or None

    def _normalize_learning_goals(
        self,
        preferences: Any,
    ) -> list[LearningGoalContext]:

        raw_goals = self._get(
            preferences,
            "learning_goals",
            [],
        )

        if raw_goals is None:
            return []

        if not isinstance(raw_goals, list):
            return []

        normalized: list[LearningGoalContext] = []

        seen: set[str] = set()

        for index, goal in enumerate(raw_goals):

            if isinstance(goal, str):

                title = self._normalize_text(goal)

                if not title:
                    continue

                key = title.casefold()

                if key in seen:
                    continue

                seen.add(key)

                normalized.append(
                    LearningGoalContext(
                        goal_id=None,
                        title=title,
                        status="active",
                    )
                )

                continue

            title = self._normalize_text(
                self._get(goal, "title")
            )

            if not title:
                continue

            key = title.casefold()

            if key in seen:
                continue

            seen.add(key)

            status = (
                self._normalize_text(
                    self._get(goal, "status")
                )
                or "active"
            ).lower()

            priority = self._normalize_text(
                self._get(goal, "priority")
            )

            progress = self._get(
                goal,
                "progress_percentage",
                self._get(goal, "progress"),
            )

            if progress is not None:
                try:
                    progress = float(progress)
                except (TypeError, ValueError):
                    progress = None

            if (
                progress is not None
                and not 0 <= progress <= 100
            ):
                progress = None

            target_date = self._normalize_datetime(
                self._get(goal, "target_date")
            )

            goal_id = self._get(goal, "id")

            normalized.append(
                LearningGoalContext(
                    goal_id=(
                        str(goal_id)
                        if goal_id is not None
                        else str(index)
                    ),
                    title=title,
                    priority=priority,
                    status=status,
                    progress_percentage=progress,
                    target_date=target_date,
                )
            )

        return normalized

    def _build_base_recommendation_context(
        self,
        user: Any,
        request: Any = None,
        interactions: list[Any] | None = None,
    ):

        preferences = self._get(
            user,
            "preferences",
        )

        if preferences is None:
            preferences = {}

        # The existing context builder expects string learning goals.
        # Phase 16.2 stores structured goal objects, so create a
        # non-mutating compatibility view containing goal titles.
        normalized_goals = self._normalize_learning_goals(
            preferences
        )

        preference_view = {
            "preferred_language": self._get(
                preferences,
                "preferred_language",
            ),
            "education_level": self._get(
                preferences,
                "education_level",
            ),
            "preferred_subjects": self._get(
                preferences,
                "preferred_subjects",
                [],
            ),
            "learning_goals": [
                goal.title
                for goal in normalized_goals
            ],
        }

        user_view = {
            "id": self._get(user, "id"),
            "preferences": preference_view,
            "resource_interactions": self._get(
                user,
                "resource_interactions",
                [],
            ),
        }

        return self.context_builder.build(
            user=user_view,
            request=request,
            interactions=interactions,
        )

    def _build_behavioral_evidence(
        self,
        signals: list[Any] | None,
        now: datetime,
    ) -> BehavioralEvidenceSummary:

        signals = signals or []

        if not isinstance(signals, list):
            raise TypeError("signals must be a list")

        positive = 0
        negative = 0
        neutral = 0

        confidence_values: list[float] = []
        strength_values: list[float] = []

        weighted_strengths: list[tuple[float, float]] = []

        latest_activity: datetime | None = None

        for signal in signals:

            strength = self._get(
                signal,
                "signal_strength",
            )

            confidence = self._get(
                signal,
                "confidence",
            )

            if (
                isinstance(strength, bool)
                or not isinstance(strength, (int, float))
                or not -1 <= strength <= 1
            ):
                continue

            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0 <= confidence <= 1
            ):
                continue

            strength = float(strength)
            confidence = float(confidence)

            occurred_at = self._normalize_datetime(
                self._get(
                    signal,
                    "occurred_at",
                )
            )

            if occurred_at is None:
                continue

            age_days = max(
                0.0,
                (now - occurred_at).total_seconds() / 86400,
            )

            # Half-life of 30 days.
            recency_weight = 0.5 ** (age_days / 30.0)

            effective_weight = (
                confidence * recency_weight
            )

            if strength > 0:
                positive += 1
            elif strength < 0:
                negative += 1
            else:
                neutral += 1

            confidence_values.append(confidence)
            strength_values.append(strength)

            weighted_strengths.append(
                (
                    strength,
                    effective_weight,
                )
            )

            if (
                latest_activity is None
                or occurred_at > latest_activity
            ):
                latest_activity = occurred_at

        total = positive + negative + neutral

        if confidence_values:
            average_confidence = (
                sum(confidence_values)
                / len(confidence_values)
            )
        else:
            average_confidence = 0.0

        total_weight = sum(
            weight
            for _, weight in weighted_strengths
        )

        if total_weight > 0:

            average_strength = sum(
                strength * weight
                for strength, weight in weighted_strengths
            ) / total_weight

        else:
            average_strength = 0.0

        coverage = min(
            1.0,
            total / self.sparse_evidence_threshold,
        )

        return BehavioralEvidenceSummary(
            total_signals=total,
            positive_signals=positive,
            negative_signals=negative,
            neutral_signals=neutral,
            average_confidence=average_confidence,
            average_signal_strength=average_strength,
            evidence_coverage=coverage,
            latest_activity_at=latest_activity,
        )

    @staticmethod
    def _build_feedback_evidence(
        feedback_collection: Any = None,
    ) -> FeedbackEvidenceSummary:

        if feedback_collection is None:
            return FeedbackEvidenceSummary(
                total_feedback=0,
                positive_feedback=0,
                negative_feedback=0,
                feedback_confidence=0.0,
            )

        total = int(
            PersonalizedContextEngine._get(
                feedback_collection,
                "total_feedback",
                0,
            )
        )

        positive = int(
            PersonalizedContextEngine._get(
                feedback_collection,
                "positive_feedback",
                0,
            )
        )

        negative = int(
            PersonalizedContextEngine._get(
                feedback_collection,
                "negative_feedback",
                0,
            )
        )

        if min(total, positive, negative) < 0:
            raise ValueError(
                "Feedback counts cannot be negative"
            )

        if positive + negative > total:
            raise ValueError(
                "Positive and negative feedback exceed total feedback"
            )

        insights = PersonalizedContextEngine._get(
            feedback_collection,
            "insights",
            [],
        )

        if insights:
            confidences = [
                float(
                    PersonalizedContextEngine._get(
                        insight,
                        "confidence",
                        0.0,
                    )
                )
                for insight in insights
            ]

            feedback_confidence = (
                sum(confidences) / len(confidences)
            )

        else:
            feedback_confidence = 0.0

        return FeedbackEvidenceSummary(
            total_feedback=total,
            positive_feedback=positive,
            negative_feedback=negative,
            feedback_confidence=feedback_confidence,
        )

    def _build_personalization_confidence(
        self,
        goals: list[LearningGoalContext],
        behavioral: BehavioralEvidenceSummary,
        feedback: FeedbackEvidenceSummary,
    ) -> PersonalizationConfidence:

        profile_evidence = len(goals)

        profile_confidence = min(
            1.0,
            profile_evidence / 3.0,
        )

        behavioral_confidence = (
            behavioral.average_confidence
            * behavioral.evidence_coverage
        )

        feedback_coverage = min(
            1.0,
            feedback.total_feedback / 3.0,
        )

        feedback_confidence = (
            feedback.feedback_confidence
            * feedback_coverage
        )

        evidence_count = (
            profile_evidence
            + behavioral.total_signals
            + feedback.total_feedback
        )

        # Explicit profile, behavior and feedback are weighted
        # independently. Missing sources contribute zero rather
        # than being interpreted as negative evidence.
        overall_confidence = (
            0.30 * profile_confidence
            + 0.35 * behavioral_confidence
            + 0.35 * feedback_confidence
        )

        overall_confidence = min(
            1.0,
            max(0.0, overall_confidence),
        )

        is_sparse = (
            evidence_count < self.sparse_evidence_threshold
        )

        if is_sparse:
            confidence_level = "sparse"

        elif overall_confidence >= 0.75:
            confidence_level = "high"

        elif overall_confidence >= 0.40:
            confidence_level = "moderate"

        else:
            confidence_level = "low"

        return PersonalizationConfidence(
            profile_confidence=profile_confidence,
            behavioral_confidence=behavioral_confidence,
            feedback_confidence=feedback_confidence,
            overall_confidence=overall_confidence,
            evidence_count=evidence_count,
            is_sparse=is_sparse,
            confidence_level=confidence_level,
        )

    def build(
        self,
        user: Any,
        request: Any = None,
        interactions: list[Any] | None = None,
        behavioral_signals: list[Any] | None = None,
        feedback_collection: Any = None,
        generated_at: datetime | None = None,
    ) -> PersonalizedLearningContext:

        if user is None:
            raise ValueError("A user is required")

        user_id = self._get(user, "id")

        if not isinstance(user_id, UUID):
            raise ValueError("A valid user UUID is required")

        now = self._normalize_datetime(
            generated_at or datetime.now(timezone.utc)
        )

        if now is None:
            raise ValueError("generated_at must be a valid datetime")

        preferences = self._get(
            user,
            "preferences",
        )

        goals = self._normalize_learning_goals(
            preferences
        )

        recommendation_context = (
            self._build_base_recommendation_context(
                user=user,
                request=request,
                interactions=interactions,
            )
        )

        behavioral = self._build_behavioral_evidence(
            signals=behavioral_signals,
            now=now,
        )

        feedback = self._build_feedback_evidence(
            feedback_collection
        )

        confidence = self._build_personalization_confidence(
            goals=goals,
            behavioral=behavioral,
            feedback=feedback,
        )

        data_sources = []

        if preferences is not None:
            data_sources.append("user_preferences")

        if interactions:
            data_sources.append("resource_interactions")

        if behavioral.total_signals:
            data_sources.append("behavioral_signals")

        if feedback.total_feedback:
            data_sources.append("recommendation_feedback")

        return PersonalizedLearningContext(
            user_id=user_id,
            recommendation_context=recommendation_context,
            learning_goals=goals,
            behavioral_evidence=behavioral,
            feedback_evidence=feedback,
            personalization_confidence=confidence,
            generated_at=now,
            data_sources=data_sources,
        )