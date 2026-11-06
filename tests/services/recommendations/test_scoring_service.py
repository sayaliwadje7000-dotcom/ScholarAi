from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.schemas.recommendations import (
    LearningContext,
    RecommendationWeights,
    RecommendationScoreBreakdown,
)

from app.schemas.recommendation_context import (
    RecommendationContext,
    RecommendationIntent,
)

from app.schemas.resource_metadata import (
    ResourceClassification,
)

from app.services.recommendations.scoring_service import (
    RecommendationScoringService,
)


@pytest.fixture
def service():
    return RecommendationScoringService()


@pytest.fixture
def context():
    return RecommendationContext(
        learning_context=LearningContext(
            user_id=uuid4(),
            preferred_language="english",
            education_level="Undergraduate",
            preferred_subjects=[
                "Data Structures",
            ],
            learning_goals=[
                "Understand binary trees",
            ],
            recent_interactions=[],
        ),
        intent=RecommendationIntent(
            query="Learn binary trees",
            subject="Data Structures",
            difficulty_level="beginner",
            language="english",
        ),
    )


@pytest.fixture
def resource():
    return ResourceClassification(
        resource_id=str(uuid4()),
        title="Introduction to Binary Trees",
        resource_type="video",
        subject="Data Structures",
        difficulty="beginner",
        language="english",
        category_slugs=["data-structures"],
        topics=[
            "Binary Trees",
            "Tree Traversal",
        ],
        keywords=[
            "BST",
            "Tree Nodes",
        ],
        learning_objectives=[
            "Understand binary trees",
        ],
        prerequisites=[],
        content_format="video",
        estimated_duration_minutes=25,
        quality_score=4.5,
        published_at=datetime.now(timezone.utc),
    )


def test_scoring_service_initializes(service):
    assert service.ALGORITHM_VERSION == "rule-based-v1"
    assert service.weights is not None


def test_topic_relevance_is_normalized(service, resource, context):
    score = service.calculate_topic_relevance(resource, context)
    assert 0.0 <= score <= 1.0


def test_learning_level_exact_match(service, resource, context):
    assert service.calculate_learning_level(resource, context) == 1.0


def test_learning_level_adjacent_match(service, resource, context):
    resource.difficulty = "intermediate"

    assert service.calculate_learning_level(resource, context) == 0.5


def test_learning_level_incompatible(service, resource, context):
    resource.difficulty = "advanced"

    assert service.calculate_learning_level(resource, context) == 0.0


def test_learning_level_unknown_is_neutral(service, resource, context):
    resource.difficulty = None

    assert service.calculate_learning_level(resource, context) == 0.5


def test_prerequisite_compatibility_without_prerequisites(
    service,
    resource,
    context,
):
    resource.prerequisites = []

    assert (
        service.calculate_prerequisite_compatibility(
            resource,
            context,
        )
        == 1.0
    )


def test_prerequisite_compatibility_unknown_mastery(
    service,
    resource,
    context,
):
    resource.prerequisites = ["Linked Lists"]

    assert (
        service.calculate_prerequisite_compatibility(
            resource,
            context,
        )
        == 0.5
    )


def test_resource_quality_normalization(service, resource):
    resource.quality_score = 4.0

    assert service.calculate_resource_quality(resource) == 0.8


def test_resource_quality_missing_is_neutral(service, resource):
    resource.quality_score = None

    assert service.calculate_resource_quality(resource) == 0.5


def test_learning_objective_relevance(service, resource, context):
    score = service.calculate_learning_objective_relevance(
        resource,
        context,
    )

    assert 0.0 <= score <= 1.0
    assert score > 0.0


def test_learning_objective_missing_is_neutral(
    service,
    resource,
    context,
):
    resource.learning_objectives = []

    assert (
        service.calculate_learning_objective_relevance(
            resource,
            context,
        )
        == 0.5
    )


def test_freshness_recent_resource(service, resource):
    reference_time = datetime.now(timezone.utc)
    resource.published_at = reference_time

    assert (
        service.calculate_freshness(
            resource,
            reference_time,
        )
        == 1.0
    )


def test_freshness_half_life(service, resource):
    reference_time = datetime.now(timezone.utc)

    resource.published_at = (
        reference_time - timedelta(days=365)
    )

    assert service.calculate_freshness(
        resource,
        reference_time,
    ) == pytest.approx(0.5)


def test_freshness_missing_date_is_neutral(service, resource):
    resource.published_at = None

    assert service.calculate_freshness(resource) == 0.5


def test_base_score_is_normalized(service, resource, context):
    breakdown = service.calculate_breakdown(
        resource,
        context,
    )

    score = service.calculate_base_score(breakdown)

    assert 0.0 <= score <= 1.0


def test_base_score_uses_configured_weights():
    weights = RecommendationWeights(
        topic_relevance=0.35,
        learning_level=0.20,
        prerequisite_compatibility=0.15,
        resource_quality=0.15,
        learning_objective=0.10,
        freshness=0.05,
    )

    service = RecommendationScoringService(weights=weights)

    breakdown = RecommendationScoreBreakdown(
        topic_relevance=1.0,
        learning_level=1.0,
        prerequisite_compatibility=1.0,
        resource_quality=1.0,
        learning_objective=1.0,
        freshness=1.0,
    )

    assert service.calculate_base_score(
        breakdown
    ) == pytest.approx(1.0)


def test_score_returns_scoring_result(service, resource, context):
    result = service.score(resource, context)

    assert result is not None
    assert str(result.resource_id) == resource.resource_id
    assert 0.0 <= result.score <= 1.0
    assert result.algorithm_version == "rule-based-v1"


def test_score_returns_none_for_excluded_resource(
    resource,
    context,
):
    from app.schemas.recommendation_rules import (
        RecommendationRule,
        RecommendationRuleConfiguration,
        RuleCondition,
        RuleEffect,
        RuleField,
        RuleOperator,
        RuleType,
    )

    rule = RecommendationRule(
        rule_id="resource.quality.exclude",
        name="Exclude Low Quality",
        description="Exclude resources with low quality scores.",
        rule_type=RuleType.EXCLUSION,
        condition=RuleCondition(
            field=RuleField.QUALITY_SCORE,
            operator=RuleOperator.LESS_THAN,
            value=3.0,
        ),
        effect=RuleEffect.EXCLUDE,
    )

    service = RecommendationScoringService(
        rule_configuration=RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    resource.quality_score = 2.0

    result = service.score(resource, context)

    assert result is None


def test_score_is_deterministic(service, resource, context):
    reference_time = datetime.now(timezone.utc)

    first = service.score(
        resource,
        context,
        reference_time,
    )

    second = service.score(
        resource,
        context,
        reference_time,
    )

    assert first.score == second.score
    assert first.breakdown == second.breakdown


def test_score_rejects_wrong_resource_type(service, context):
    with pytest.raises(TypeError):
        service.score({}, context)


def test_score_rejects_wrong_context_type(service, resource):
    with pytest.raises(TypeError):
        service.score(resource, {})