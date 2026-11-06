from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.recommendations import (
    LearningContext,
    RecommendationScoreBreakdown,
    RecommendationScoringResult,
    RecommendationWeights,
)

from app.schemas.recommendation_context import (
    RecommendationContext,
    RecommendationIntent,
)

from app.schemas.resource_metadata import (
    ResourceClassification,
)

from app.services.recommendations.ranking_service import (
    RankedRecommendation,
)

from app.services.recommendations.explanation_service import (
    RecommendationExplanationService,
)

from app.services.recommendations.explanation_pipeline import (
    RecommendationExplanationPipeline,
)


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
        category_slugs=[
            "data-structures",
        ],
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
        is_active=True,
        published_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def ranked_recommendation(resource):

    resource_id = uuid4()

    resource = resource.model_copy(
        update={
            "resource_id": str(resource_id),
        }
    )

    breakdown = RecommendationScoreBreakdown(
        topic_relevance=0.95,
        learning_level=1.0,
        prerequisite_compatibility=1.0,
        resource_quality=0.90,
        learning_objective=0.95,
        freshness=0.85,
    )

    weights = RecommendationWeights(
        topic_relevance=0.35,
        learning_level=0.20,
        prerequisite_compatibility=0.15,
        resource_quality=0.15,
        learning_objective=0.10,
        freshness=0.05,
    )

    scoring_result = RecommendationScoringResult(
        resource_id=resource_id,
        score=0.95,
        breakdown=breakdown,
        weights=weights,
        algorithm_version="rule-based-v1",
    )

    return RankedRecommendation(
        resource=resource,
        scoring_result=scoring_result,
        rank_position=1,
    )


@pytest.fixture
def explanation_service():

    return RecommendationExplanationService()


def test_explanation_service_initializes(
    explanation_service,
):

    assert (
        explanation_service.EXPLANATION_VERSION
        == "v1"
    )


def test_explanation_returns_valid_schema(
    explanation_service,
    ranked_recommendation,
    context,
):

    result = explanation_service.explain(
        ranked_recommendation,
        context,
    )

    assert result.resource_id == (
        ranked_recommendation.resource_id
    )

    assert result.rank_position == 1

    assert 0.0 <= result.recommendation_score <= 1.0

    assert result.algorithm_version == "rule-based-v1"


def test_explanation_contains_all_six_factors(
    explanation_service,
    ranked_recommendation,
    context,
):

    result = explanation_service.explain(
        ranked_recommendation,
        context,
    )

    assert len(result.factors) == 6


def test_explanation_preserves_factor_weights(
    explanation_service,
    ranked_recommendation,
    context,
):

    result = explanation_service.explain(
        ranked_recommendation,
        context,
    )

    assert sum(
        factor.weight for factor in result.factors
    ) == pytest.approx(1.0)


def test_explanation_calculates_weighted_contributions(
    explanation_service,
    ranked_recommendation,
    context,
):

    result = explanation_service.explain(
        ranked_recommendation,
        context,
    )

    for factor in result.factors:

        assert factor.weighted_contribution == pytest.approx(
            factor.score * factor.weight,
            abs=0.0001,
        )


def test_explanation_selects_at_most_three_highlights(
    explanation_service,
    ranked_recommendation,
    context,
):

    result = explanation_service.explain(
        ranked_recommendation,
        context,
    )

    assert len(result.highlights) <= 3


def test_explanation_contains_reason(
    explanation_service,
    ranked_recommendation,
    context,
):

    result = explanation_service.explain(
        ranked_recommendation,
        context,
    )

    assert result.reason.strip()

    assert len(result.reason) <= 500


def test_explanation_is_deterministic(
    explanation_service,
    ranked_recommendation,
    context,
):

    first = explanation_service.explain(
        ranked_recommendation,
        context,
    )

    second = explanation_service.explain(
        ranked_recommendation,
        context,
    )

    assert first == second


def test_explanation_identifies_no_prerequisites(
    explanation_service,
    ranked_recommendation,
    context,
):

    result = explanation_service.explain(
        ranked_recommendation,
        context,
    )

    prerequisite_factor = next(
        factor
        for factor in result.factors
        if factor.factor == "Prerequisite Compatibility"
    )

    assert "No prerequisite topics" in (
        prerequisite_factor.description
    )


def test_explanation_does_not_claim_mastery(
    explanation_service,
    ranked_recommendation,
    context,
):

    resource = ranked_recommendation.resource.model_copy(
        update={
            "prerequisites": [
                "Linked Lists",
            ],
        }
    )

    updated = RankedRecommendation(
        resource=resource,
        scoring_result=ranked_recommendation.scoring_result,
        rank_position=1,
    )

    result = explanation_service.explain(
        updated,
        context,
    )

    prerequisite_factor = next(
        factor
        for factor in result.factors
        if factor.factor == "Prerequisite Compatibility"
    )

    assert "not been independently verified" in (
        prerequisite_factor.description
    )


def test_explanation_handles_missing_quality_rating(
    explanation_service,
    ranked_recommendation,
    context,
):

    resource = ranked_recommendation.resource.model_copy(
        update={
            "quality_score": None,
        }
    )

    updated = RankedRecommendation(
        resource=resource,
        scoring_result=ranked_recommendation.scoring_result,
        rank_position=1,
    )

    result = explanation_service.explain(
        updated,
        context,
    )

    quality_factor = next(
        factor
        for factor in result.factors
        if factor.factor == "Resource Quality"
    )

    assert "No resource quality rating" in (
        quality_factor.description
    )


def test_explanation_handles_missing_publication_date(
    explanation_service,
    ranked_recommendation,
    context,
):

    resource = ranked_recommendation.resource.model_copy(
        update={
            "published_at": None,
        }
    )

    updated = RankedRecommendation(
        resource=resource,
        scoring_result=ranked_recommendation.scoring_result,
        rank_position=1,
    )

    result = explanation_service.explain(
        updated,
        context,
    )

    freshness_factor = next(
        factor
        for factor in result.factors
        if factor.factor == "Content Freshness"
    )

    assert "No publication date" in (
        freshness_factor.description
    )


def test_explanation_rejects_wrong_ranked_type(
    explanation_service,
    context,
):

    with pytest.raises(TypeError):

        explanation_service.explain(
            {},
            context,
        )


def test_explanation_rejects_wrong_context_type(
    explanation_service,
    ranked_recommendation,
):

    with pytest.raises(TypeError):

        explanation_service.explain(
            ranked_recommendation,
            {},
        )


def test_explanation_pipeline_generates_multiple_explanations(
    ranked_recommendation,
    context,
):

    second = RankedRecommendation(
        resource=ranked_recommendation.resource,
        scoring_result=ranked_recommendation.scoring_result,
        rank_position=2,
    )

    pipeline = RecommendationExplanationPipeline()

    results = pipeline.execute(
        [
            ranked_recommendation,
            second,
        ],
        context,
    )

    assert len(results) == 2

    assert results[0].rank_position == 1

    assert results[1].rank_position == 2


def test_explanation_pipeline_preserves_order(
    ranked_recommendation,
    context,
):

    second = RankedRecommendation(
        resource=ranked_recommendation.resource,
        scoring_result=ranked_recommendation.scoring_result,
        rank_position=2,
    )

    pipeline = RecommendationExplanationPipeline()

    results = pipeline.execute(
        [
            second,
            ranked_recommendation,
        ],
        context,
    )

    assert [
        result.rank_position for result in results
    ] == [
        2,
        1,
    ]


def test_explanation_pipeline_handles_empty_list(context):

    pipeline = RecommendationExplanationPipeline()

    results = pipeline.execute(
        [],
        context,
    )

    assert results == []