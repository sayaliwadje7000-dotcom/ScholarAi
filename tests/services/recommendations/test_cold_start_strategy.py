from types import SimpleNamespace

import pytest

from app.schemas.sparse_data import (
    ColdStartStrategy,
    SparseDataLevel,
)
from app.services.recommendations.cold_start_strategy import (
    ColdStartStrategyService,
)


def make_assessment(
    *,
    strategy=ColdStartStrategy.GENERAL_DISCOVERY,
    exploration_ratio=0.8,
    personalization_strength=0.0,
    use_profile=False,
    use_behavior=False,
    use_feedback=False,
    fallback=True,
    is_sparse=True,
):
    policy = SimpleNamespace(
        strategy=strategy,
        exploration_ratio=exploration_ratio,
        personalization_strength=personalization_strength,
        use_explicit_preferences=use_profile,
        use_behavioral_signals=use_behavior,
        use_explicit_feedback=use_feedback,
        use_general_fallback=fallback,
        preserve_hard_constraints=True,
        treat_missing_evidence_as_neutral=True,
    )

    return SimpleNamespace(
        policy=policy,
        is_sparse=is_sparse,
        data_level=SparseDataLevel.COLD_START,
    )


def test_general_discovery_strategy():
    service = ColdStartStrategyService()

    result = service.build_strategy(
        make_assessment()
    )

    assert result.strategy == ColdStartStrategy.GENERAL_DISCOVERY
    assert result.exploration_ratio == 0.8
    assert result.personalization_strength == 0.0
    assert result.include_general_candidates is True


def test_profile_preferences_are_preserved():
    service = ColdStartStrategyService()

    result = service.build_strategy(
        make_assessment(
            strategy=ColdStartStrategy.PROFILE_GUIDED_DISCOVERY,
            exploration_ratio=0.65,
            personalization_strength=0.25,
            use_profile=True,
        )
    )

    assert result.use_profile_preferences is True
    assert result.use_behavioral_signals is False


def test_behavior_and_feedback_can_be_enabled_independently():
    service = ColdStartStrategyService()

    result = service.build_strategy(
        make_assessment(
            strategy=ColdStartStrategy.FULL_PERSONALIZATION,
            exploration_ratio=0.2,
            personalization_strength=0.9,
            use_profile=True,
            use_behavior=True,
            use_feedback=False,
            fallback=False,
            is_sparse=False,
        )
    )

    assert result.use_profile_preferences is True
    assert result.use_behavioral_signals is True
    assert result.use_explicit_feedback is False
    assert result.include_general_candidates is False


def test_hard_constraints_and_neutral_missing_evidence_are_preserved():
    service = ColdStartStrategyService()

    result = service.build_strategy(
        make_assessment()
    )

    assert result.preserve_hard_constraints is True
    assert result.missing_evidence_is_neutral is True


def test_missing_assessment_is_rejected():
    service = ColdStartStrategyService()

    with pytest.raises(ValueError):
        service.build_strategy(None)