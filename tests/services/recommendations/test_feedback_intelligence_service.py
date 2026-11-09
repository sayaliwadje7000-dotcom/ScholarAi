from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.recommendation import Recommendation
from app.models.recommendation_feedback import RecommendationFeedback

from app.services.recommendations.feedback_intelligence_service import (
    FeedbackIntelligenceService,
)


@pytest.fixture
def service():
    return FeedbackIntelligenceService()


@pytest.fixture
def recommendation():
    return Recommendation(
        id=uuid4(),
        user_id=uuid4(),
        resource_id=uuid4(),
        recommendation_type="personalized",
        score=0.85,
        rank_position=1,
        reason="Matches the student's learning preferences.",
        algorithm_version="v1",
    )


def make_feedback(recommendation, feedback_type):
    return RecommendationFeedback(
        id=uuid4(),
        recommendation_id=recommendation.id,
        feedback_type=feedback_type,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.parametrize(
    ("feedback_type", "expected_strength", "expected_label"),
    [
        ("helpful", 1.0, 1),
        ("not_helpful", -1.0, 0),
        ("irrelevant", -1.0, 0),
    ],
)
def test_process_feedback_generates_correct_insight(
    service,
    recommendation,
    feedback_type,
    expected_strength,
    expected_label,
):
    feedback = make_feedback(
        recommendation,
        feedback_type,
    )

    insight = service.process_feedback(
        feedback,
        recommendation,
    )

    assert insight.feedback_type == feedback_type
    assert insight.signal_strength == expected_strength
    assert insight.label.label == expected_label
    assert insight.user_id == recommendation.user_id
    assert insight.resource_id == recommendation.resource_id
    assert insight.confidence == 1.0


@pytest.mark.parametrize(
    "feedback_type",
    [
        " helpful ",
        "HELPFUL",
        "Not_Helpful",
        "IRRELEVANT",
    ],
)
def test_feedback_type_is_normalized(
    service,
    feedback_type,
):
    normalized = service.normalize_feedback_type(
        feedback_type
    )

    assert normalized == feedback_type.strip().lower()


@pytest.mark.parametrize(
    "feedback_type",
    [
        "",
        "unknown",
        "positive",
        "negative",
        "view",
        None,
    ],
)
def test_invalid_feedback_type_is_rejected(
    service,
    feedback_type,
):
    with pytest.raises((TypeError, ValueError)):
        service.normalize_feedback_type(feedback_type)


def test_feedback_recommendation_mismatch_is_rejected(
    service,
    recommendation,
):
    feedback = make_feedback(
        recommendation,
        "helpful",
    )

    feedback.recommendation_id = uuid4()

    with pytest.raises(ValueError):
        service.process_feedback(
            feedback,
            recommendation,
        )


def test_naive_timestamp_is_normalized_to_utc():
    value = datetime(2026, 11, 9, 10, 30)

    normalized = FeedbackIntelligenceService.normalize_timestamp(
        value
    )

    assert normalized.tzinfo == timezone.utc


def test_aware_timestamp_is_converted_to_utc():
    from datetime import timedelta

    value = datetime(
        2026,
        11,
        9,
        10,
        30,
        tzinfo=timezone(timedelta(hours=5, minutes=30)),
    )

    normalized = FeedbackIntelligenceService.normalize_timestamp(
        value
    )

    assert normalized.hour == 5
    assert normalized.minute == 0
    assert normalized.tzinfo == timezone.utc


def test_collection_counts_positive_and_negative_feedback(
    service,
    recommendation,
):
    helpful = make_feedback(
        recommendation,
        "helpful",
    )

    not_helpful = make_feedback(
        recommendation,
        "not_helpful",
    )

    irrelevant = make_feedback(
        recommendation,
        "irrelevant",
    )

    events = [
        (helpful, recommendation),
        (not_helpful, recommendation),
        (irrelevant, recommendation),
    ]

    collection = service.build_insights(
        user_id=recommendation.user_id,
        events=events,
    )

    assert collection.total_feedback == 3
    assert collection.positive_feedback == 1
    assert collection.negative_feedback == 2


def test_empty_collection_is_supported(service):
    user_id = uuid4()

    collection = service.build_insights(
        user_id=user_id,
        events=[],
    )

    assert collection.user_id == user_id
    assert collection.total_feedback == 0
    assert collection.positive_feedback == 0
    assert collection.negative_feedback == 0
    assert collection.insights == []


def test_other_users_feedback_is_rejected(
    service,
    recommendation,
):
    other_user_id = uuid4()

    feedback = make_feedback(
        recommendation,
        "helpful",
    )

    with pytest.raises(ValueError):
        service.build_insights(
            user_id=other_user_id,
            events=[(feedback, recommendation)],
        )


@pytest.mark.parametrize(
    "limit",
    [
        0,
        -1,
        501,
    ],
)
def test_invalid_limit_is_rejected(limit):
    with pytest.raises(ValueError):
        FeedbackIntelligenceService(limit=limit)


@pytest.mark.parametrize(
    "limit",
    [
        True,
        1.5,
        "100",
    ],
)
def test_non_integer_limit_is_rejected(limit):
    with pytest.raises(TypeError):
        FeedbackIntelligenceService(limit=limit)