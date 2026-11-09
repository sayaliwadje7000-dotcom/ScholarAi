from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.behavioral_signals import (
    BehavioralSignalSource,
    BehavioralSignal,
)

from app.services.recommendations.personalized_context_engine import (
    PersonalizedContextEngine,
)


@pytest.fixture
def engine():
    return PersonalizedContextEngine()


@pytest.fixture
def sample_user():
    return SimpleNamespace(
        id=uuid4(),
        preferences=SimpleNamespace(
            preferred_language="EN",
            education_level="Undergraduate",
            preferred_subjects=[
                "Computer Science",
                "Mathematics",
            ],
            learning_goals=[
                {
                    "id": "goal-1",
                    "title": "Master Python",
                    "priority": "high",
                    "status": "active",
                    "progress_percentage": 35,
                },
                {
                    "id": "goal-2",
                    "title": "Learn Machine Learning",
                    "priority": "medium",
                    "status": "active",
                    "progress_percentage": 10,
                },
            ],
        ),
        resource_interactions=[],
    )


@pytest.fixture
def generated_at():
    return datetime(
        2026,
        11,
        9,
        12,
        0,
        tzinfo=timezone.utc,
    )


def make_signal(
    strength=1.0,
    confidence=0.9,
    occurred_at=None,
):
    return BehavioralSignal(
        source=BehavioralSignalSource.LEARNING_ACTIVITY,
        source_event_id=uuid4(),
        event_type="study_session_completed",
        entity_type="study_session",
        entity_id=uuid4(),
        resource_id=None,
        signal_strength=strength,
        confidence=confidence,
        duration_seconds=120,
        occurred_at=(
            occurred_at
            or datetime.now(timezone.utc)
        ),
        metadata={},
    )


def test_build_returns_personalized_context(
    engine,
    sample_user,
    generated_at,
):
    context = engine.build(
        user=sample_user,
        generated_at=generated_at,
    )

    assert context.user_id == sample_user.id
    assert context.context_version == "personalized-v1"
    assert context.generated_at == generated_at


def test_build_preserves_existing_recommendation_context(
    engine,
    sample_user,
):
    context = engine.build(
        user=sample_user,
    )

    base = context.recommendation_context

    assert base.learning_context.user_id == sample_user.id
    assert base.learning_context.preferred_language == "en"
    assert "Computer Science" in (
        base.learning_context.preferred_subjects
    )


def test_structured_goals_are_normalized(
    engine,
    sample_user,
):
    context = engine.build(
        user=sample_user,
    )

    assert len(context.learning_goals) == 2

    assert context.learning_goals[0].title == "Master Python"
    assert context.learning_goals[0].priority == "high"
    assert context.learning_goals[0].progress_percentage == 35


def test_legacy_string_goals_are_supported():
    user = SimpleNamespace(
        id=uuid4(),
        preferences=SimpleNamespace(
            preferred_language="en",
            education_level="Undergraduate",
            preferred_subjects=[],
            learning_goals=[
                "Learn Python",
                "Understand databases",
            ],
        ),
        resource_interactions=[],
    )

    context = PersonalizedContextEngine().build(user)

    assert len(context.learning_goals) == 2
    assert context.learning_goals[0].title == "Learn Python"


def test_duplicate_goals_are_removed(
    engine,
):
    user = SimpleNamespace(
        id=uuid4(),
        preferences=SimpleNamespace(
            preferred_subjects=[],
            learning_goals=[
                "Learn Python",
                " learn python ",
            ],
        ),
        resource_interactions=[],
    )

    context = engine.build(user)

    assert len(context.learning_goals) == 1


def test_completed_goals_are_preserved(
    engine,
):
    user = SimpleNamespace(
        id=uuid4(),
        preferences=SimpleNamespace(
            preferred_subjects=[],
            learning_goals=[
                {
                    "id": "goal-1",
                    "title": "Complete Python",
                    "status": "completed",
                    "progress_percentage": 100,
                }
            ],
        ),
        resource_interactions=[],
    )

    context = engine.build(user)

    assert context.learning_goals[0].status == "completed"
    assert context.learning_goals[0].progress_percentage == 100


def test_behavioral_evidence_is_aggregated(
    engine,
    sample_user,
    generated_at,
):
    signals = [
        make_signal(
            strength=1.0,
            confidence=0.9,
            occurred_at=generated_at,
        ),
        make_signal(
            strength=-1.0,
            confidence=0.8,
            occurred_at=generated_at,
        ),
        make_signal(
            strength=0.0,
            confidence=0.7,
            occurred_at=generated_at,
        ),
    ]

    context = engine.build(
        user=sample_user,
        behavioral_signals=signals,
        generated_at=generated_at,
    )

    evidence = context.behavioral_evidence

    assert evidence.total_signals == 3
    assert evidence.positive_signals == 1
    assert evidence.negative_signals == 1
    assert evidence.neutral_signals == 1
    assert evidence.average_confidence == pytest.approx(0.8)


def test_behavioral_recency_weighting(
    engine,
    sample_user,
    generated_at,
):
    recent = make_signal(
        strength=1.0,
        confidence=1.0,
        occurred_at=generated_at,
    )

    old = make_signal(
        strength=-1.0,
        confidence=1.0,
        occurred_at=generated_at - timedelta(days=30),
    )

    context = engine.build(
        user=sample_user,
        behavioral_signals=[recent, old],
        generated_at=generated_at,
    )

    # A 30-day-old signal receives half the recency weight
    # of a signal observed at the current context time.
    assert context.behavioral_evidence.average_signal_strength == pytest.approx(
        1 / 3
    )


def test_empty_behavioral_evidence_is_supported(
    engine,
    sample_user,
):
    context = engine.build(
        user=sample_user,
        behavioral_signals=[],
    )

    assert context.behavioral_evidence.total_signals == 0
    assert context.behavioral_evidence.average_confidence == 0


def test_feedback_evidence_is_aggregated(
    engine,
    sample_user,
):
    feedback = SimpleNamespace(
        total_feedback=4,
        positive_feedback=3,
        negative_feedback=1,
        insights=[
            SimpleNamespace(confidence=1.0),
            SimpleNamespace(confidence=0.8),
            SimpleNamespace(confidence=0.9),
            SimpleNamespace(confidence=0.7),
        ],
    )

    context = engine.build(
        user=sample_user,
        feedback_collection=feedback,
    )

    evidence = context.feedback_evidence

    assert evidence.total_feedback == 4
    assert evidence.positive_feedback == 3
    assert evidence.negative_feedback == 1
    assert evidence.feedback_confidence == pytest.approx(0.85)


def test_missing_feedback_is_not_negative(
    engine,
    sample_user,
):
    context = engine.build(
        user=sample_user,
        feedback_collection=None,
    )

    assert context.feedback_evidence.total_feedback == 0
    assert context.feedback_evidence.negative_feedback == 0


def test_sparse_profile_is_identified():
    user = SimpleNamespace(
        id=uuid4(),
        preferences=SimpleNamespace(
            preferred_subjects=[],
            learning_goals=[],
        ),
        resource_interactions=[],
    )

    context = PersonalizedContextEngine().build(user)

    confidence = context.personalization_confidence

    assert confidence.is_sparse is True
    assert confidence.confidence_level == "sparse"
    assert confidence.evidence_count == 0


def test_dense_evidence_is_not_marked_sparse(
    engine,
    sample_user,
    generated_at,
):
    signals = [
        make_signal(
            occurred_at=generated_at,
        )
        for _ in range(5)
    ]

    context = engine.build(
        user=sample_user,
        behavioral_signals=signals,
        generated_at=generated_at,
    )

    assert (
        context.personalization_confidence.is_sparse
        is False
    )


def test_overall_confidence_is_bounded(
    engine,
    sample_user,
    generated_at,
):
    signals = [
        make_signal(
            confidence=1.0,
            occurred_at=generated_at,
        )
        for _ in range(10)
    ]

    feedback = SimpleNamespace(
        total_feedback=10,
        positive_feedback=10,
        negative_feedback=0,
        insights=[
            SimpleNamespace(confidence=1.0)
            for _ in range(10)
        ],
    )

    context = engine.build(
        user=sample_user,
        behavioral_signals=signals,
        feedback_collection=feedback,
        generated_at=generated_at,
    )

    confidence = context.personalization_confidence

    assert 0 <= confidence.overall_confidence <= 1
    assert 0 <= confidence.profile_confidence <= 1
    assert 0 <= confidence.behavioral_confidence <= 1
    assert 0 <= confidence.feedback_confidence <= 1


def test_original_preferences_are_not_modified(
    engine,
    sample_user,
):
    original_goals = list(
        sample_user.preferences.learning_goals
    )

    original_subjects = list(
        sample_user.preferences.preferred_subjects
    )

    engine.build(sample_user)

    assert (
        sample_user.preferences.learning_goals
        == original_goals
    )

    assert (
        sample_user.preferences.preferred_subjects
        == original_subjects
    )


def test_missing_user_is_rejected(engine):
    with pytest.raises(ValueError):
        engine.build(None)


def test_invalid_user_id_is_rejected(engine):
    user = SimpleNamespace(
        id="not-a-uuid",
        preferences=None,
    )

    with pytest.raises(ValueError):
        engine.build(user)


@pytest.mark.parametrize(
    "threshold",
    [
        0,
        -1,
        True,
        1.5,
    ],
)
def test_invalid_sparse_threshold_is_rejected(threshold):
    with pytest.raises(ValueError):
        PersonalizedContextEngine(
            sparse_evidence_threshold=threshold
        )


def test_invalid_behavioral_signal_list_is_rejected(
    engine,
    sample_user,
):
    with pytest.raises(TypeError):
        engine.build(
            user=sample_user,
            behavioral_signals="invalid",
        )


def test_inconsistent_feedback_counts_are_rejected(
    engine,
    sample_user,
):
    feedback = SimpleNamespace(
        total_feedback=2,
        positive_feedback=2,
        negative_feedback=2,
        insights=[],
    )

    with pytest.raises(ValueError):
        engine.build(
            user=sample_user,
            feedback_collection=feedback,
        )