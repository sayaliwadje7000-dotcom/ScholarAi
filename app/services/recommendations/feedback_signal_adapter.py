from __future__ import annotations

from app.schemas.behavioral_signals import (
    BehavioralSignal,
    BehavioralSignalSource,
)

from app.schemas.recommendation_feedback_intelligence import (
    RecommendationFeedbackInsight,
)


class RecommendationFeedbackSignalAdapter:
    """
    Converts recommendation feedback insights into
    Phase 16.3 behavioral signals.
    """

    @staticmethod
    def to_behavioral_signal(
        insight: RecommendationFeedbackInsight,
    ) -> BehavioralSignal:

        return BehavioralSignal(
            source=BehavioralSignalSource.RECOMMENDATION_FEEDBACK,
            source_event_id=insight.feedback_id,
            event_type=insight.feedback_type,
            entity_type="study_resource",
            entity_id=insight.resource_id,
            resource_id=insight.resource_id,
            signal_strength=insight.signal_strength,
            confidence=insight.confidence,
            duration_seconds=None,
            occurred_at=insight.occurred_at,
            metadata={
                "recommendation_id": str(
                    insight.recommendation_id
                ),
                "label": insight.label.label,
                "label_source": insight.label.label_source,
                "source_event": insight.label.source_event,
            },
        )

    @classmethod
    def convert_collection(
        cls,
        insights: list[RecommendationFeedbackInsight],
    ) -> list[BehavioralSignal]:

        return [
            cls.to_behavioral_signal(insight)
            for insight in insights
        ]