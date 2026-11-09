from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.adaptive_recommendations import (
    AdaptationMode,
    AdaptationReason,
    AdaptiveRecommendationPolicy,
)
from app.services.recommendations.adaptive_hybrid_service import (
    AdaptiveHybridService,
)


class FakeContextEngine:
    def __init__(self, context):
        self.context = context
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return self.context


class FakePolicyEngine:
    def __init__(self):
        self.calls = []

    def build_policy(self, context):
        self.calls.append(context)

        return AdaptiveRecommendationPolicy(
            mode=AdaptationMode.PROFILE_GUIDED,
            profile_weight=1.0,
            behavioral_weight=0.0,
            feedback_weight=0.0,
            evidence_confidence=0.8,
            reasons=(
                AdaptationReason.EXPLICIT_SUBJECT_PREFERENCES,
            ),
        )


def make_personalized_context(user_id):
    """
    Construct a context matching the Phase 16.5
    PersonalizedLearningContext contract.
    """

    learning_context = SimpleNamespace(
        user_id=user_id,
        preferred_language="English",
        education_level="Undergraduate",
        preferred_subjects=["Computer Science"],
        learning_goals=["Learn Data Structures"],
        recent_interactions=[],
    )

    recommendation_context = SimpleNamespace(
        learning_context=learning_context,
        intent=SimpleNamespace(
            query=None,
            subject=None,
            resource_types=[],
            difficulty_level=None,
            language=None,
            recommendation_type="personalized",
            exclude_completed=False,
        ),
        context_version="v1",
    )

    return SimpleNamespace(
        user_id=user_id,
        context_version="v1",
        recommendation_context=recommendation_context,
        goals=[
            SimpleNamespace(
                goal_id="goal-1",
                title="Learn Data Structures",
            )
        ],
        behavioral_evidence=SimpleNamespace(
            total_signals=0,
            positive_signals=0,
            negative_signals=0,
            neutral_signals=0,
            average_confidence=0.0,
            average_signal_strength=0.0,
            evidence_coverage=0.0,
            latest_activity_at=None,
        ),
        feedback_evidence=SimpleNamespace(
            total_feedback=0,
            positive_feedback=0,
            negative_feedback=0,
            feedback_confidence=0.0,
        ),
        confidence=SimpleNamespace(
            profile_confidence=0.8,
            behavioral_confidence=0.0,
            feedback_confidence=0.0,
            overall_confidence=0.8,
            evidence_count=0,
            is_sparse=True,
            confidence_level="medium",
        ),
        generated_at=None,
        data_sources=("user_preferences",),
    )


def test_service_builds_context_and_calls_hybrid_executor():
    user_id = uuid4()
    user = SimpleNamespace(id=user_id)

    personalized_context = make_personalized_context(user_id)
    context_engine = FakeContextEngine(personalized_context)

    hybrid_result = {
        "recommendations": ["resource-1"]
    }

    executor_calls = []

    def executor(context, *, limit=None):
        executor_calls.append((context, limit))
        return hybrid_result

    policy_engine = FakePolicyEngine()

    service = AdaptiveHybridService(
        personalized_context_engine=context_engine,
        hybrid_executor=executor,
        policy_engine=policy_engine,
    )

    hybrid_context = object()

    result = service.generate(
        user=user,
        hybrid_context=hybrid_context,
        limit=10,
    )

    assert result.user_id == user_id
    assert result.recommendations == hybrid_result
    assert result.personalization_context is personalized_context
    assert result.adaptation_applied is False

    assert executor_calls == [(hybrid_context, 10)]

    assert len(context_engine.calls) == 1
    assert len(policy_engine.calls) == 1

    assert result.policy.mode == AdaptationMode.PROFILE_GUIDED


def test_service_passes_behavioral_and_feedback_evidence():
    user_id = uuid4()
    user = SimpleNamespace(id=user_id)

    personalized_context = make_personalized_context(user_id)
    context_engine = FakeContextEngine(personalized_context)

    def executor(context, *, limit=None):
        return []

    service = AdaptiveHybridService(
        personalized_context_engine=context_engine,
        hybrid_executor=executor,
    )

    hybrid_context = object()

    interactions = [object()]
    signals = [object()]
    feedback = object()

    service.generate(
        user=user,
        hybrid_context=hybrid_context,
        interactions=interactions,
        behavioral_signals=signals,
        feedback_collection=feedback,
    )

    assert len(context_engine.calls) == 1

    call = context_engine.calls[0]

    assert call["user"] is user
    assert call["interactions"] is interactions
    assert call["behavioral_signals"] is signals
    assert call["feedback_collection"] is feedback


def test_service_rejects_user_context_mismatch():
    user = SimpleNamespace(id=uuid4())

    context_engine = FakeContextEngine(
        make_personalized_context(uuid4())
    )

    service = AdaptiveHybridService(
        personalized_context_engine=context_engine,
        hybrid_executor=lambda context, limit=None: [],
    )

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        service.generate(
            user=user,
            hybrid_context=object(),
        )


@pytest.mark.parametrize(
    "limit",
    [0, -1],
)
def test_service_rejects_non_positive_limit(limit):
    user_id = uuid4()
    user = SimpleNamespace(id=user_id)

    context_engine = FakeContextEngine(
        make_personalized_context(user_id)
    )

    service = AdaptiveHybridService(
        personalized_context_engine=context_engine,
        hybrid_executor=lambda context, limit=None: [],
    )

    with pytest.raises(ValueError):
        service.generate(
            user=user,
            hybrid_context=object(),
            limit=limit,
        )


@pytest.mark.parametrize(
    "limit",
    [True, 1.5, "10"],
)
def test_service_rejects_invalid_limit_type(limit):
    user_id = uuid4()
    user = SimpleNamespace(id=user_id)

    context_engine = FakeContextEngine(
        make_personalized_context(user_id)
    )

    service = AdaptiveHybridService(
        personalized_context_engine=context_engine,
        hybrid_executor=lambda context, limit=None: [],
    )

    with pytest.raises(TypeError):
        service.generate(
            user=user,
            hybrid_context=object(),
            limit=limit,
        )


def test_service_rejects_non_uuid_user_id():
    user = SimpleNamespace(id="not-a-uuid")

    service = AdaptiveHybridService(
        personalized_context_engine=FakeContextEngine(None),
        hybrid_executor=lambda context, limit=None: [],
    )

    with pytest.raises(
        ValueError,
        match="UUID",
    ):
        service.generate(
            user=user,
            hybrid_context=object(),
        )