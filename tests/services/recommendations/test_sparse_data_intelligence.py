from types import SimpleNamespace

import pytest

from app.schemas.sparse_data import (
    ColdStartStrategy,
    SparseDataLevel,
)
from app.services.recommendations.sparse_data_intelligence import (
    SparseDataIntelligenceService,
)


def make_context(
    *,
    subjects=None,
    goals=None,
    behavioral_count=0,
    behavioral_confidence=0.0,
    feedback_count=0,
    feedback_confidence=0.0,
    profile_confidence=0.0,
    overall_confidence=0.0,
):
    learning_context = SimpleNamespace(
        preferred_subjects=subjects or [],
        preferred_language=None,
        education_level=None,
        learning_goals=[],
    )

    return SimpleNamespace(
        recommendation_context=SimpleNamespace(
            learning_context=learning_context
        ),
        goals=goals or [],
        behavioral_evidence=SimpleNamespace(
            total_signals=behavioral_count,
            positive_signals=0,
            negative_signals=0,
            neutral_signals=behavioral_count,
        ),
        feedback_evidence=SimpleNamespace(
            total_feedback=feedback_count,
            positive_feedback=0,
            negative_feedback=0,
            feedback_confidence=feedback_confidence,
        ),
        confidence=SimpleNamespace(
            profile_confidence=profile_confidence,
            behavioral_confidence=behavioral_confidence,
            feedback_confidence=feedback_confidence,
            overall_confidence=overall_confidence,
        ),
    )


def test_no_history_user_gets_exploration_first():
    service = SparseDataIntelligenceService()

    result = service.evaluate(
        personalized_context=make_context(),
        candidate_pool_size=10,
    )

    assert result.assessment.data_level == SparseDataLevel.NO_DATA

    assert (
        result.strategy.strategy
        == ColdStartStrategy.GENERAL_DISCOVERY
    )

    assert result.allocation.exploration_count == 8
    assert result.allocation.personalized_count == 2


def test_profile_guided_user_gets_balanced_candidate_plan():
    service = SparseDataIntelligenceService()

    result = service.evaluate(
        personalized_context=make_context(
            subjects=["Computer Science"],
            goals=["Learn Python"],
            profile_confidence=0.8,
            overall_confidence=0.4,
        ),
        candidate_pool_size=20,
    )

    assert (
        result.strategy.strategy
        == ColdStartStrategy.PROFILE_GUIDED_DISCOVERY
    )

    assert result.allocation.exploration_count == 13
    assert result.allocation.personalized_count == 7


def test_candidate_allocation_matches_requested_pool():
    service = SparseDataIntelligenceService()

    for pool_size in range(0, 31):
        result = service.evaluate(
            personalized_context=make_context(),
            candidate_pool_size=pool_size,
        )

        assert result.allocation.total_count == pool_size

        assert (
            result.allocation.exploration_count
            + result.allocation.personalized_count
            == pool_size
        )


@pytest.mark.parametrize(
    "pool_size",
    [-1, -5],
)
def test_negative_candidate_pool_is_rejected(pool_size):
    service = SparseDataIntelligenceService()

    with pytest.raises(ValueError):
        service.evaluate(
            personalized_context=make_context(),
            candidate_pool_size=pool_size,
        )


@pytest.mark.parametrize(
    "pool_size",
    [True, 1.5, "10"],
)
def test_invalid_candidate_pool_type_is_rejected(pool_size):
    service = SparseDataIntelligenceService()

    with pytest.raises(TypeError):
        service.evaluate(
            personalized_context=make_context(),
            candidate_pool_size=pool_size,
        )