from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.hybrid.contracts import (
    ComponentScore,
    ComponentStatus,
    HybridCandidate,
    HybridContractError,
    HybridRecommendationBatch,
    RecommendationComponent,
    RecommendationProvenance,
    ScoreDirection,
)


@pytest.fixture
def timestamp():
    return datetime.now(timezone.utc)


@pytest.fixture
def resource_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def available_rule_score(timestamp):
    return ComponentScore(
        component=RecommendationComponent.RULE_BASED,
        status=ComponentStatus.AVAILABLE,
        value=0.85,
        calculated_at=timestamp,
    )


@pytest.fixture
def available_content_score(timestamp):
    return ComponentScore(
        component=RecommendationComponent.CONTENT_BASED,
        status=ComponentStatus.AVAILABLE,
        value=0.92,
        calculated_at=timestamp,
    )


@pytest.fixture
def available_ml_score(timestamp):
    return ComponentScore(
        component=RecommendationComponent.MACHINE_LEARNING,
        status=ComponentStatus.AVAILABLE,
        value=0.73,
        model_version="baseline-v1",
        calculated_at=timestamp,
    )


@pytest.fixture
def provenance(timestamp):
    return RecommendationProvenance(
        component=RecommendationComponent.RULE_BASED,
        source_name="internal_recommendation_engine",
        source_id="rule-engine",
        retrieved_at=timestamp,
    )


@pytest.fixture
def candidate(
    resource_id,
    available_rule_score,
    provenance,
    timestamp,
):
    return HybridCandidate(
        resource_id=resource_id,
        title="Introduction to Machine Learning",
        resource_type="course",
        component_scores=(
            available_rule_score,
        ),
        provenance=(
            provenance,
        ),
        canonical_url="https://example.com/ml-course",
        description="An introductory machine learning course.",
        metadata={
            "difficulty": "beginner",
            "language": "English",
        },
        discovered_at=timestamp,
    )


def test_available_component_score_is_valid(
    available_rule_score,
):
    assert available_rule_score.value == 0.85

    assert (
        available_rule_score.status
        == ComponentStatus.AVAILABLE
    )


def test_unavailable_component_can_have_no_score(timestamp):
    score = ComponentScore(
        component=RecommendationComponent.MACHINE_LEARNING,
        status=ComponentStatus.UNAVAILABLE,
        value=None,
        reason="Model is not loaded.",
        calculated_at=timestamp,
    )

    assert score.value is None

    assert score.status == ComponentStatus.UNAVAILABLE


def test_failed_component_can_have_no_score(timestamp):
    score = ComponentScore(
        component=RecommendationComponent.CONTENT_BASED,
        status=ComponentStatus.FAILED,
        reason="Content scoring failed.",
        calculated_at=timestamp,
    )

    assert score.value is None

    assert score.status == ComponentStatus.FAILED


def test_available_component_requires_score(timestamp):
    with pytest.raises(HybridContractError):
        ComponentScore(
            component=RecommendationComponent.RULE_BASED,
            status=ComponentStatus.AVAILABLE,
            value=None,
            calculated_at=timestamp,
        )


def test_unavailable_component_rejects_numeric_score(timestamp):
    with pytest.raises(HybridContractError):
        ComponentScore(
            component=RecommendationComponent.MACHINE_LEARNING,
            status=ComponentStatus.UNAVAILABLE,
            value=0.5,
            calculated_at=timestamp,
        )


@pytest.mark.parametrize(
    "invalid_value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
        "0.5",
    ],
)
def test_component_score_rejects_invalid_numeric_values(
    timestamp,
    invalid_value,
):
    with pytest.raises(HybridContractError):
        ComponentScore(
            component=RecommendationComponent.RULE_BASED,
            status=ComponentStatus.AVAILABLE,
            value=invalid_value,
            calculated_at=timestamp,
        )


def test_raw_score_is_not_restricted_to_zero_and_one(timestamp):
    score = ComponentScore(
        component=RecommendationComponent.CONTENT_BASED,
        status=ComponentStatus.AVAILABLE,
        value=-0.35,
        calculated_at=timestamp,
    )

    assert score.value == -0.35


def test_lower_is_better_direction_is_supported(timestamp):
    score = ComponentScore(
        component=RecommendationComponent.CONTENT_BASED,
        status=ComponentStatus.AVAILABLE,
        value=0.25,
        direction=ScoreDirection.LOWER_IS_BETTER,
        calculated_at=timestamp,
    )

    assert score.direction == ScoreDirection.LOWER_IS_BETTER


def test_component_score_requires_timezone_aware_datetime():
    with pytest.raises(HybridContractError):
        ComponentScore(
            component=RecommendationComponent.RULE_BASED,
            status=ComponentStatus.AVAILABLE,
            value=0.8,
            calculated_at=datetime(2026, 1, 1),
        )


def test_provenance_rejects_empty_source_name(timestamp):
    with pytest.raises(HybridContractError):
        RecommendationProvenance(
            component=RecommendationComponent.RULE_BASED,
            source_name=" ",
            retrieved_at=timestamp,
        )


def test_candidate_accepts_valid_data(candidate, resource_id):
    assert candidate.resource_id == resource_id

    assert candidate.title == "Introduction to Machine Learning"

    assert candidate.resource_type == "course"


def test_candidate_rejects_non_uuid_resource_id(
    available_rule_score,
    provenance,
    timestamp,
):
    with pytest.raises(HybridContractError):
        HybridCandidate(
            resource_id="123",
            title="Machine Learning",
            resource_type="course",
            component_scores=(available_rule_score,),
            provenance=(provenance,),
            discovered_at=timestamp,
        )


def test_candidate_rejects_empty_title(
    resource_id,
    available_rule_score,
    provenance,
    timestamp,
):
    with pytest.raises(HybridContractError):
        HybridCandidate(
            resource_id=resource_id,
            title=" ",
            resource_type="course",
            component_scores=(available_rule_score,),
            provenance=(provenance,),
            discovered_at=timestamp,
        )


def test_candidate_rejects_duplicate_component_scores(
    resource_id,
    available_rule_score,
    timestamp,
    provenance,
):
    duplicate_score = ComponentScore(
        component=RecommendationComponent.RULE_BASED,
        status=ComponentStatus.AVAILABLE,
        value=0.75,
        calculated_at=timestamp,
    )

    with pytest.raises(HybridContractError):
        HybridCandidate(
            resource_id=resource_id,
            title="Machine Learning",
            resource_type="course",
            component_scores=(
                available_rule_score,
                duplicate_score,
            ),
            provenance=(provenance,),
            discovered_at=timestamp,
        )


def test_candidate_rejects_invalid_component_score_type(
    resource_id,
    provenance,
    timestamp,
):
    with pytest.raises(HybridContractError):
        HybridCandidate(
            resource_id=resource_id,
            title="Machine Learning",
            resource_type="course",
            component_scores=(0.8,),
            provenance=(provenance,),
            discovered_at=timestamp,
        )


def test_candidate_can_retain_all_three_component_scores(
    resource_id,
    available_rule_score,
    available_content_score,
    available_ml_score,
    provenance,
    timestamp,
):
    candidate = HybridCandidate(
        resource_id=resource_id,
        title="Machine Learning",
        resource_type="course",
        component_scores=(
            available_rule_score,
            available_content_score,
            available_ml_score,
        ),
        provenance=(provenance,),
        discovered_at=timestamp,
    )

    assert len(candidate.component_scores) == 3

    assert len(candidate.available_components()) == 3


def test_candidate_get_component_score(candidate):
    result = candidate.get_component_score(
        RecommendationComponent.RULE_BASED
    )

    assert result is not None

    assert result.value == 0.85


def test_candidate_returns_none_for_missing_component(candidate):
    result = candidate.get_component_score(
        RecommendationComponent.MACHINE_LEARNING
    )

    assert result is None


def test_candidate_available_components(candidate):
    assert candidate.available_components() == (
        RecommendationComponent.RULE_BASED,
    )


def test_candidate_failed_components(
    resource_id,
    provenance,
    timestamp,
):
    failed_score = ComponentScore(
        component=RecommendationComponent.MACHINE_LEARNING,
        status=ComponentStatus.FAILED,
        reason="Prediction failed.",
        calculated_at=timestamp,
    )

    candidate = HybridCandidate(
        resource_id=resource_id,
        title="Machine Learning",
        resource_type="course",
        component_scores=(failed_score,),
        provenance=(provenance,),
        discovered_at=timestamp,
    )

    assert candidate.failed_components() == (
        RecommendationComponent.MACHINE_LEARNING,
    )


def test_hybrid_batch_accepts_valid_candidates(
    candidate,
    user_id,
):
    batch = HybridRecommendationBatch(
        request_id=uuid4(),
        user_id=user_id,
        candidates=(candidate,),
    )

    assert len(batch.candidates) == 1

    assert batch.user_id == user_id


def test_hybrid_batch_rejects_invalid_user_id(candidate):
    with pytest.raises(HybridContractError):
        HybridRecommendationBatch(
            request_id=uuid4(),
            user_id="invalid-user-id",
            candidates=(candidate,),
        )


def test_hybrid_batch_rejects_invalid_candidate_type(user_id):
    with pytest.raises(HybridContractError):
        HybridRecommendationBatch(
            request_id=uuid4(),
            user_id=user_id,
            candidates=("invalid-candidate",),
        )


def test_provenance_can_represent_multiple_components(
    resource_id,
    available_rule_score,
    available_content_score,
    timestamp,
):
    rule_provenance = RecommendationProvenance(
        component=RecommendationComponent.RULE_BASED,
        source_name="rule_engine",
        retrieved_at=timestamp,
    )

    content_provenance = RecommendationProvenance(
        component=RecommendationComponent.CONTENT_BASED,
        source_name="content_engine",
        retrieved_at=timestamp,
    )

    candidate = HybridCandidate(
        resource_id=resource_id,
        title="Machine Learning",
        resource_type="course",
        component_scores=(
            available_rule_score,
            available_content_score,
        ),
        provenance=(
            rule_provenance,
            content_provenance,
        ),
        discovered_at=timestamp,
    )

    assert len(candidate.provenance) == 2