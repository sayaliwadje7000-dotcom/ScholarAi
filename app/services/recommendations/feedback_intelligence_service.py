from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.recommendation_feedback import RecommendationFeedback

from app.schemas.recommendation_feedback_intelligence import (
    RecommendationFeedbackInsight,
    RecommendationFeedbackInsightCollection,
    RecommendationFeedbackLabel,
)

from app.services.recommendations.ml.dataset_schema import (
    DatasetLabel,
)

from app.services.recommendations.ml.labeling import (
    RecommendationFeedbackSignal,
    label_recommendation_feedback,
)


class FeedbackIntelligenceService:
    """
    Converts explicit recommendation feedback into normalized
    personalization insights and ML training labels.

    This service does not create feedback records. Feedback
    persistence remains the responsibility of the existing
    recommendation feedback API.
    """

    POSITIVE_FEEDBACK = {
        "helpful",
    }

    NEGATIVE_FEEDBACK = {
        "not_helpful",
        "irrelevant",
    }

    SIGNAL_STRENGTHS = {
        "helpful": 1.0,
        "not_helpful": -1.0,
        "irrelevant": -1.0,
    }

    DEFAULT_LIMIT = 100
    MAX_LIMIT = 500

    def __init__(self, limit: int = DEFAULT_LIMIT) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer")

        if not 1 <= limit <= self.MAX_LIMIT:
            raise ValueError(
                f"limit must be between 1 and {self.MAX_LIMIT}"
            )

        self.limit = limit

    @staticmethod
    def normalize_feedback_type(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("feedback_type must be a string")

        normalized = value.strip().lower()

        allowed = (
            FeedbackIntelligenceService.POSITIVE_FEEDBACK
            | FeedbackIntelligenceService.NEGATIVE_FEEDBACK
        )

        if normalized not in allowed:
            raise ValueError("Unsupported recommendation feedback type")

        return normalized

    @staticmethod
    def normalize_timestamp(value: datetime) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError("Feedback timestamp must be a datetime")

        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    @staticmethod
    def _get_feedback_timestamp(
        feedback: RecommendationFeedback,
    ) -> datetime:
        timestamp = feedback.created_at

        if timestamp is None:
            raise ValueError(
                "Persisted recommendation feedback must have created_at"
            )

        return FeedbackIntelligenceService.normalize_timestamp(
            timestamp
        )

    def load_feedback_events(
        self,
        db: Session,
        user_id: UUID,
    ) -> list[tuple[RecommendationFeedback, Recommendation]]:
        """
        Load feedback belonging to the specified user.

        Ownership is resolved through Recommendation.user_id.
        Feedback records belonging to other users are excluded
        by the database query.
        """

        statement = (
            select(
                RecommendationFeedback,
                Recommendation,
            )
            .join(
                Recommendation,
                RecommendationFeedback.recommendation_id
                == Recommendation.id,
            )
            .where(
                Recommendation.user_id == user_id,
            )
            .order_by(
                RecommendationFeedback.created_at.desc(),
                RecommendationFeedback.id.desc(),
            )
            .limit(self.limit)
        )

        rows = db.execute(statement).all()

        return [
            (feedback, recommendation)
            for feedback, recommendation in rows
        ]

    def process_feedback(
        self,
        feedback: RecommendationFeedback,
        recommendation: Recommendation,
    ) -> RecommendationFeedbackInsight:
        """
        Convert one persisted feedback record into a normalized
        personalization insight.
        """

        if feedback.recommendation_id != recommendation.id:
            raise ValueError(
                "Feedback and recommendation identifiers do not match"
            )

        feedback_type = self.normalize_feedback_type(
            feedback.feedback_type
        )

        timestamp = self._get_feedback_timestamp(feedback)

        training_signal = RecommendationFeedbackSignal(
            user_id=recommendation.user_id,
            resource_id=recommendation.resource_id,
            feedback_type=feedback_type,
            created_at=timestamp,
        )

        training_example = label_recommendation_feedback(
            training_signal
        )

        if training_example is None:
            raise ValueError(
                "Supported explicit feedback did not produce a label"
            )

        label_value = training_example.label

        return RecommendationFeedbackInsight(
            feedback_id=feedback.id,
            recommendation_id=recommendation.id,
            user_id=recommendation.user_id,
            resource_id=recommendation.resource_id,
            feedback_type=feedback_type,
            signal_strength=self.SIGNAL_STRENGTHS[feedback_type],
            confidence=training_example.confidence,
            label=RecommendationFeedbackLabel(
                user_id=training_example.user_id,
                resource_id=training_example.resource_id,
                label=label_value,
                label_source=training_example.label_source.value,
                source_event=training_example.source_event,
                confidence=training_example.confidence,
                observed_at=training_example.observed_at,
            ),
            occurred_at=timestamp,
        )

    def build_insights(
        self,
        user_id: UUID,
        events: list[
            tuple[RecommendationFeedback, Recommendation]
        ],
    ) -> RecommendationFeedbackInsightCollection:
        """
        Build a user-scoped collection of feedback insights.
        """

        insights: list[RecommendationFeedbackInsight] = []

        for feedback, recommendation in events:
            if recommendation.user_id != user_id:
                raise ValueError(
                    "Feedback collection contains another user's data"
                )

            insights.append(
                self.process_feedback(
                    feedback=feedback,
                    recommendation=recommendation,
                )
            )

        positive_count = sum(
            insight.signal_strength > 0
            for insight in insights
        )

        negative_count = sum(
            insight.signal_strength < 0
            for insight in insights
        )

        return RecommendationFeedbackInsightCollection(
            user_id=user_id,
            total_feedback=len(insights),
            positive_feedback=positive_count,
            negative_feedback=negative_count,
            insights=insights,
        )

    def get_user_feedback_insights(
        self,
        db: Session,
        user_id: UUID,
    ) -> RecommendationFeedbackInsightCollection:
        """
        Public service entry point for Phase 16.5 and later.
        """

        events = self.load_feedback_events(
            db=db,
            user_id=user_id,
        )

        return self.build_insights(
            user_id=user_id,
            events=events,
        )