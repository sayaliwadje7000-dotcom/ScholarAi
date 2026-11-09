from types import SimpleNamespace

import pytest

from app.schemas.adaptive_recommendations import AdaptationMode
from app.services.recommendations.adaptive_policy_engine import (
    AdaptivePolicyEngine,
)


def make_context(
    *,
    profile_confidence=0.0,
    behavioral_confidence=0.0,
    feedback_confidence=0.0,
    overall_confidence=0.0,
    is_sparse=True,
    subjects=None,
    goals=None,
    total_signals=0,
    total_feedback=0,
):
    learning_context = SimpleNamespace(
        preferred_subjects=subjects or [],
        learning_goals=goals or [],
        preferred_language=None,
        education_level=None,
    )

    recommendation_context = SimpleNamespace(
        learning_context=learning_context
    )

    return SimpleNamespace(
        confidence=SimpleNamespace(
            profile_confidence=profile_confidence,
            behavioral_confidence=behavioral_confidence,
            feedback_confidence=feedback_confidence,
            overall_confidence=overall_confidence,
            is_sparse=is_sparse,
        ),
        behavioral_evidence=SimpleNamespace(
            total_signals=total_signals
        ),
        feedback_evidence=SimpleNamespace(
            total_feedback=total_feedback
        ),
        recommendation_context=recommendation_context,
        goals=goals or [],
    )


def test_empty_context_uses_cold_start():
    engine = AdaptivePolicyEngine()

    policy = engine.build_policy(make_context())

    assert policy.mode == AdaptationMode.COLD_START
    assert policy.profile_weight == 0
    assert policy.behavioral_weight == 0
    assert policy.feedback_weight == 0


def test_profile_only_context_uses_profile_guided_mode():
    engine = AdaptivePolicyEngine()

    context = make_context(
        profile_confidence=0.8,
        overall_confidence=0.8,
        is_sparse=True,
        subjects=["Computer Science"],
    )

    policy = engine.build_policy(context)

    assert policy.mode == AdaptationMode.PROFILE_GUIDED
    assert policy.profile_weight == 1.0


def test_behavioral_context_uses_behavior_guided_mode():
    engine = AdaptivePolicyEngine()

    context = make_context(
        behavioral_confidence=0.8,
        overall_confidence=0.7,
        total_signals=10,
    )

    policy = engine.build_policy(context)

    assert policy.mode == AdaptationMode.BEHAVIOR_GUIDED
    assert policy.behavioral_weight == 1.0


def test_feedback_context_uses_feedback_guided_mode():
    engine = AdaptivePolicyEngine()

    context = make_context(
        feedback_confidence=0.9,
        overall_confidence=0.9,
        total_feedback=5,
    )

    policy = engine.build_policy(context)

    assert policy.mode == AdaptationMode.FEEDBACK_GUIDED
    assert policy.feedback_weight == 1.0


def test_dense_profile_behavior_and_feedback_use_full_personalization():
    engine = AdaptivePolicyEngine()

    context = make_context(
        profile_confidence=0.8,
        behavioral_confidence=0.8,
        feedback_confidence=0.9,
        overall_confidence=0.85,
        is_sparse=False,
        subjects=["Computer Science"],
        goals=["Learn Data Structures"],
        total_signals=20,
        total_feedback=8,
    )

    policy = engine.build_policy(context)

    assert policy.mode == AdaptationMode.FULL_PERSONALIZATION

    assert (
        policy.profile_weight
        + policy.behavioral_weight
        + policy.feedback_weight
    ) == pytest.approx(1.0)


def test_missing_behavior_does_not_create_behavior_weight():
    engine = AdaptivePolicyEngine()

    context = make_context(
        profile_confidence=0.8,
        behavioral_confidence=0.9,
        feedback_confidence=0.0,
        overall_confidence=0.8,
        subjects=["Mathematics"],
        total_signals=0,
        total_feedback=0,
    )

    policy = engine.build_policy(context)

    assert policy.behavioral_weight == 0.0
    assert policy.feedback_weight == 0.0


@pytest.mark.parametrize(
    "value",
    [-1.0, 0.0, 0.5, 1.0, 2.0, None, "invalid"],
)
def test_confidence_values_are_bounded(value):
    engine = AdaptivePolicyEngine()

    context = make_context(
        profile_confidence=value,
        overall_confidence=value,
        subjects=["Mathematics"],
    )

    policy = engine.build_policy(context)

    assert 0.0 <= policy.profile_weight <= 1.0
    assert 0.0 <= policy.evidence_confidence <= 1.0


def test_policy_does_not_modify_input_context():
    engine = AdaptivePolicyEngine()

    context = make_context(
        profile_confidence=0.8,
        subjects=["Mathematics"],
    )

    original_subjects = list(
        context.recommendation_context.learning_context.preferred_subjects
    )

    engine.build_policy(context)

    assert (
        context.recommendation_context.learning_context.preferred_subjects
        == original_subjects
    )