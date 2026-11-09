from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.recommendation_api import (
    RecommendationFeedbackCreate,
)

from app.schemas.recommendation_feedback_intelligence import (
    RecommendationFeedbackLabel,
    RecommendationFeedbackInsight,
    RecommendationFeedbackInsightCollection,
)


def test_feedback_request_normalizes_feedback_type():
    request = RecommendationFeedbackCreate(
        feedback_type=" HELPFUL "
    )

    assert request.feedback_type == "helpful"


def test_feedback_request_normalizes_comment():
    request = RecommendationFeedbackCreate(
        feedback_type="helpful",
        comment="  Useful recommendation.  ",
    )

    assert request.comment == "Useful recommendation."


def test_blank_comment_becomes_none():
    request = RecommendationFeedbackCreate(
        feedback_type="helpful",
        comment="   ",
    )

    assert request.comment is None


def test_invalid_feedback_type_is_rejected():
    with pytest.raises(ValidationError):
        RecommendationFeedbackCreate(
            feedback_type="unknown"
        )


def test_feedback_label_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        RecommendationFeedbackLabel(
            user_id=uuid4(),
            resource_id=uuid4(),
            label=1,
            label_source="explicit_feedback",
            source_event="helpful",
            confidence=1.5,
            observed_at=datetime.now(timezone.utc),
        )


def test_feedback_label_preserves_integer_value():
    label = RecommendationFeedbackLabel(
        user_id=uuid4(),
        resource_id=uuid4(),
        label=1,
        label_source="explicit_feedback",
        source_event="helpful",
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )

    assert label.label == 1
    assert isinstance(label.label, int)


def test_feedback_insight_rejects_invalid_strength():
    timestamp = datetime.now(timezone.utc)
    user_id = uuid4()
    resource_id = uuid4()

    label = RecommendationFeedbackLabel(
        user_id=user_id,
        resource_id=resource_id,
        label=1,
        label_source="explicit_feedback",
        source_event="helpful",
        confidence=1.0,
        observed_at=timestamp,
    )

    with pytest.raises(ValidationError):
        RecommendationFeedbackInsight(
            feedback_id=uuid4(),
            recommendation_id=uuid4(),
            user_id=user_id,
            resource_id=resource_id,
            feedback_type="helpful",
            signal_strength=2.0,
            confidence=1.0,
            label=label,
            occurred_at=timestamp,
        )


def test_empty_feedback_collection_is_valid():
    collection = RecommendationFeedbackInsightCollection(
        user_id=uuid4(),
        total_feedback=0,
        positive_feedback=0,
        negative_feedback=0,
        insights=[],
    )

    assert collection.total_feedback == 0
    assert collection.positive_feedback == 0
    assert collection.negative_feedback == 0
    assert collection.insights == []