from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.behavioral_signals import (
    BehavioralSignalSource,
)

from app.schemas.recommendation_feedback_intelligence import (
    RecommendationFeedbackInsight,
    RecommendationFeedbackLabel,
)

from app.services.recommendations.feedback_signal_adapter import (
    RecommendationFeedbackSignalAdapter,
)


@pytest.fixture
def insight():
    user_id = uuid4()
    resource_id = uuid4()
    feedback_id = uuid4()
    recommendation_id = uuid4()

    timestamp = datetime.now(timezone.utc)

    label = RecommendationFeedbackLabel(
        user_id=user_id,
        resource_id=resource_id,
        label=1,
        label_source="explicit_feedback",
        source_event="helpful",
        confidence=1.0,
        observed_at=timestamp,
    )

    return RecommendationFeedbackInsight(
        feedback_id=feedback_id,
        recommendation_id=recommendation_id,
        user_id=user_id,
        resource_id=resource_id,
        feedback_type="helpful",
        signal_strength=1.0,
        confidence=1.0,
        label=label,
        occurred_at=timestamp,
    )


def test_adapter_preserves_feedback_identity(insight):
    signal = (
        RecommendationFeedbackSignalAdapter
        .to_behavioral_signal(insight)
    )

    assert signal.source_event_id == insight.feedback_id
    assert signal.resource_id == insight.resource_id
    assert signal.signal_strength == 1.0


def test_adapter_uses_recommendation_feedback_source(insight):
    signal = (
        RecommendationFeedbackSignalAdapter
        .to_behavioral_signal(insight)
    )

    assert (
        signal.source
        == BehavioralSignalSource.RECOMMENDATION_FEEDBACK
    )


def test_adapter_preserves_label_metadata(insight):
    signal = (
        RecommendationFeedbackSignalAdapter
        .to_behavioral_signal(insight)
    )

    assert signal.metadata["label"] == 1
    assert signal.metadata["label_source"] == "explicit_feedback"
    assert signal.metadata["source_event"] == "helpful"
    assert signal.metadata["recommendation_id"] == str(
        insight.recommendation_id
    )


def test_adapter_converts_collection(insight):
    signals = (
        RecommendationFeedbackSignalAdapter
        .convert_collection([insight, insight])
    )

    assert len(signals) == 2
    assert all(
        signal.source == BehavioralSignalSource.RECOMMENDATION_FEEDBACK
        for signal in signals
    )