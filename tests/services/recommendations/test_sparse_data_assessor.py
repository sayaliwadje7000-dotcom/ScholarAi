from types import SimpleNamespace

import pytest

from app.schemas.sparse_data import (
    ColdStartStrategy,
    SparseDataLevel,
)
from app.services.recommendations.sparse_data_assessor import (
    SparseDataAssessor,
)


def make_context(
    *,
    subjects=None,
    goals=None,
    behavioral_count=0,
    positive_signals=0,
    negative_signals=0,
    neutral_signals=0,
    behavioral_confidence=0.0,
    feedback_count=0,
    positive_feedback=0,
    negative_feedback=0,
    feedback_confidence=0.0,
    profile_confidence=0.0,
    overall_confidence=0.0,
    language=None,
    education_level=None,
):
    learning_context = SimpleNamespace(
        preferred_subjects=subjects or [],
        learning_goals=[],
        preferred_language=language,
        education_level=education_level,
    )

    recommendation_context = SimpleNamespace(
        learning_context=learning_context
    )

    return SimpleNamespace(
        recommendation_context=recommendation_context,
        goals=goals or [],
        behavioral_evidence=SimpleNamespace(
            total_signals=behavioral_count,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
            neutral_signals=neutral_signals,
            average_confidence=behavioral_confidence,
            average_signal_strength=0.0,
            evidence_coverage=0.0,
            latest_activity_at=None,
        ),
        feedback_evidence=SimpleNamespace(
            total_feedback=feedback_count,
            positive_feedback=positive_feedback,
            negative_feedback=negative_feedback,
            feedback_confidence=feedback_confidence,
        ),
        confidence=SimpleNamespace(
            profile_confidence=profile_confidence,
            behavioral_confidence=behavioral_confidence,
            feedback_confidence=feedback_confidence,
            overall_confidence=overall_confidence,
            evidence_count=(
                behavioral_count
                + feedback_count
                + len(subjects or [])
                + len(goals or [])
            ),
            is_sparse=False,
        ),
    )


def test_no_data_user_is_classified_as_no_data():
    assessor = SparseDataAssessor()

    result = assessor.assess(make_context())

    assert result.data_level == SparseDataLevel.NO_DATA
    assert result.is_cold_start is True
    assert result.is_sparse is True

    assert (
        result.policy.strategy
        == ColdStartStrategy.GENERAL_DISCOVERY
    )


def test_new_user_with_profile_is_profile_guided():
    assessor = SparseDataAssessor()

    context = make_context(
        subjects=["Computer Science"],
        goals=["Learn Python"],
        profile_confidence=0.8,
        overall_confidence=0.4,
    )

    result = assessor.assess(context)

    assert result.data_level == SparseDataLevel.LIMITED_DATA

    assert (
        result.policy.strategy
        == ColdStartStrategy.PROFILE_GUIDED_DISCOVERY
    )

    assert result.policy.use_explicit_preferences is True
    assert result.policy.use_behavioral_signals is False


def test_behavioral_history_requires_minimum_count_and_confidence():
    assessor = SparseDataAssessor()

    insufficient = make_context(
        behavioral_count=4,
        behavioral_confidence=0.9,
        overall_confidence=0.8,
    )

    sufficient = make_context(
        behavioral_count=5,
        positive_signals=3,
        negative_signals=1,
        neutral_signals=1,
        behavioral_confidence=0.8,
        overall_confidence=0.8,
    )

    insufficient_result = assessor.assess(insufficient)
    sufficient_result = assessor.assess(sufficient)

    assert (
        insufficient_result.policy.use_behavioral_signals
        is False
    )

    assert (
        sufficient_result.policy.use_behavioral_signals
        is True
    )


def test_feedback_requires_minimum_count_and_confidence():
    assessor = SparseDataAssessor()

    insufficient = make_context(
        feedback_count=2,
        positive_feedback=1,
        negative_feedback=1,
        feedback_confidence=0.9,
        overall_confidence=0.8,
    )

    sufficient = make_context(
        feedback_count=3,
        positive_feedback=2,
        negative_feedback=1,
        feedback_confidence=0.8,
        overall_confidence=0.8,
    )

    assert (
        assessor.assess(insufficient).policy.use_explicit_feedback
        is False
    )

    assert (
        assessor.assess(sufficient).policy.use_explicit_feedback
        is True
    )


def test_dense_evidence_is_classified_as_sufficient():
    assessor = SparseDataAssessor()

    context = make_context(
        subjects=["Computer Science"],
        goals=["Learn Python"],
        behavioral_count=10,
        positive_signals=7,
        negative_signals=2,
        neutral_signals=1,
        behavioral_confidence=0.9,
        feedback_count=5,
        positive_feedback=4,
        negative_feedback=1,
        feedback_confidence=0.9,
        profile_confidence=0.9,
        overall_confidence=0.9,
    )

    result = assessor.assess(context)

    assert result.data_level == SparseDataLevel.SUFFICIENT_DATA

    assert (
        result.policy.strategy
        == ColdStartStrategy.FULL_PERSONALIZATION
    )

    assert result.policy.use_behavioral_signals is True
    assert result.policy.use_explicit_feedback is True


def test_missing_feedback_is_not_negative_feedback():
    assessor = SparseDataAssessor()

    context = make_context(
        subjects=["Mathematics"],
        profile_confidence=0.8,
        overall_confidence=0.5,
    )

    result = assessor.assess(context)

    assert result.evidence.feedback_count == 0
    assert result.evidence.negative_feedback_count == 0

    assert result.policy.treat_missing_evidence_as_neutral is True


def test_missing_behavior_is_not_negative_behavior():
    assessor = SparseDataAssessor()

    context = make_context(
        subjects=["Mathematics"],
        profile_confidence=0.8,
        overall_confidence=0.5,
    )

    result = assessor.assess(context)

    assert result.evidence.behavioral_signal_count == 0
    assert result.evidence.negative_signal_count == 0


def test_hard_constraints_are_always_preserved():
    assessor = SparseDataAssessor()

    for context in (
        make_context(),
        make_context(subjects=["Mathematics"]),
        make_context(
            behavioral_count=10,
            behavioral_confidence=0.8,
            feedback_count=5,
            feedback_confidence=0.8,
            overall_confidence=0.9,
        ),
    ):
        result = assessor.assess(context)

        assert result.policy.preserve_hard_constraints is True


@pytest.mark.parametrize(
    "confidence",
    [-1.0, 0.0, 0.5, 1.0, 2.0, None, "invalid"],
)
def test_invalid_confidence_values_are_bounded(confidence):
    assessor = SparseDataAssessor()

    context = make_context(
        subjects=["Computer Science"],
        profile_confidence=confidence,
        behavioral_confidence=confidence,
        feedback_confidence=confidence,
        overall_confidence=confidence,
    )

    result = assessor.assess(context)

    assert 0.0 <= result.evidence.profile_confidence <= 1.0
    assert 0.0 <= result.evidence.behavioral_confidence <= 1.0
    assert 0.0 <= result.evidence.feedback_confidence <= 1.0
    assert 0.0 <= result.evidence.overall_confidence <= 1.0


def test_none_context_is_rejected():
    assessor = SparseDataAssessor()

    with pytest.raises(ValueError):
        assessor.assess(None)