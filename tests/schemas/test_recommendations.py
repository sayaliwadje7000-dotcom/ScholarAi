from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.recommendations import (
    DifficultyLevel,
    InteractionSummary,
    InteractionType,
    LearningContext,
    RecommendationCandidate,
    RecommendationRequest,
    RecommendationScoreBreakdown,
    RecommendationScoringResult,
    RecommendationType,
    RecommendationWeights,
    ResourceType,
)


# ============================================================
# REQUEST VALIDATION
# ============================================================


def test_recommendation_request_defaults():

    request = RecommendationRequest()

    assert request.limit == 10

    assert (
        request.recommendation_type
        == RecommendationType.PERSONALIZED
    )

    assert request.exclude_completed is True


def test_recommendation_request_normalizes_strings():

    request = RecommendationRequest(
        query="  Data Structures  ",
        subject="  Computer Science  ",
        language="EN",
    )

    assert request.query == "Data Structures"

    assert request.subject == "Computer Science"

    assert request.language == "en"


def test_recommendation_request_rejects_empty_query():

    with pytest.raises(ValidationError):

        RecommendationRequest(
            query="   "
        )


def test_recommendation_request_rejects_invalid_limit():

    with pytest.raises(ValidationError):

        RecommendationRequest(
            limit=100
        )


def test_recommendation_request_rejects_duplicate_types():

    with pytest.raises(ValidationError):

        RecommendationRequest(
            resource_types=[
                ResourceType.VIDEO,
                ResourceType.VIDEO,
            ]
        )


def test_recommendation_request_rejects_user_id():

    with pytest.raises(ValidationError):

        RecommendationRequest(
            user_id=str(uuid4())
        )


# ============================================================
# INTERACTION VALIDATION
# ============================================================


def test_rate_interaction_requires_rating():

    with pytest.raises(ValidationError):

        InteractionSummary(
            resource_id=uuid4(),
            interaction_type=InteractionType.RATE,
            occurred_at=datetime.now(timezone.utc),
        )


def test_non_rate_interaction_rejects_rating():

    with pytest.raises(ValidationError):

        InteractionSummary(
            resource_id=uuid4(),
            interaction_type=InteractionType.VIEW,
            rating=5,
            occurred_at=datetime.now(timezone.utc),
        )


def test_valid_rate_interaction():

    interaction = InteractionSummary(
        resource_id=uuid4(),
        interaction_type=InteractionType.RATE,
        rating=5,
        occurred_at=datetime.now(timezone.utc),
    )

    assert interaction.rating == 5


# ============================================================
# LEARNING CONTEXT
# ============================================================


def test_learning_context_deduplicates_preferences():

    context = LearningContext(
        user_id=uuid4(),
        preferred_subjects=[
            "Data Structures",
            "Data Structures",
            "Operating Systems",
        ],
        learning_goals=[
            "Exam Preparation",
            "Exam Preparation",
        ],
    )

    assert context.preferred_subjects == [
        "Data Structures",
        "Operating Systems",
    ]

    assert context.learning_goals == [
        "Exam Preparation",
    ]


def test_learning_context_rejects_empty_subject():

    with pytest.raises(ValidationError):

        LearningContext(
            user_id=uuid4(),
            preferred_subjects=["   "],
        )


# ============================================================
# CANDIDATE VALIDATION
# ============================================================


def test_valid_recommendation_candidate():

    candidate = RecommendationCandidate(
        resource_id=uuid4(),
        title="Introduction to Data Structures",
        resource_type=ResourceType.COURSE,
        url="https://example.com/course",
        difficulty_level=DifficultyLevel.BEGINNER,
        quality_score="4.50",
        is_active=True,
    )

    assert candidate.title == (
        "Introduction to Data Structures"
    )

    assert candidate.quality_score == 4.50


def test_candidate_rejects_negative_duration():

    with pytest.raises(ValidationError):

        RecommendationCandidate(
            resource_id=uuid4(),
            title="Algorithms",
            resource_type=ResourceType.BOOK,
            url="https://example.com/book",
            estimated_duration_minutes=-5,
            is_active=True,
        )


def test_candidate_rejects_quality_above_five():

    with pytest.raises(ValidationError):

        RecommendationCandidate(
            resource_id=uuid4(),
            title="Algorithms",
            resource_type=ResourceType.BOOK,
            url="https://example.com/book",
            quality_score="5.50",
            is_active=True,
        )


def test_candidate_normalizes_category_slugs():

    candidate = RecommendationCandidate(
        resource_id=uuid4(),
        title="Python Tutorial",
        resource_type=ResourceType.TUTORIAL,
        url="https://example.com/python",
        category_slugs=[
            " Programming ",
            "programming",
            " Python ",
        ],
        is_active=True,
    )

    assert candidate.category_slugs == [
        "programming",
        "python",
    ]


# ============================================================
# WEIGHT VALIDATION
# ============================================================


def test_default_recommendation_weights():

    weights = RecommendationWeights()

    assert weights.topic_relevance == 0.35

    assert weights.learning_level == 0.20

    assert weights.freshness == 0.05


def test_recommendation_weights_sum_to_one():

    weights = RecommendationWeights()

    total = sum(
        [
            weights.topic_relevance,
            weights.learning_level,
            weights.prerequisite_compatibility,
            weights.resource_quality,
            weights.learning_objective,
            weights.freshness,
        ]
    )

    assert total == pytest.approx(1.0)


def test_invalid_weights_are_rejected():

    with pytest.raises(ValidationError):

        RecommendationWeights(
            topic_relevance=0.50,
            learning_level=0.20,
            prerequisite_compatibility=0.15,
            resource_quality=0.15,
            learning_objective=0.10,
            freshness=0.05,
        )


# ============================================================
# SCORE VALIDATION
# ============================================================


def test_score_breakdown_rejects_values_above_one():

    with pytest.raises(ValidationError):

        RecommendationScoreBreakdown(
            topic_relevance=1.5,
            learning_level=0.8,
            prerequisite_compatibility=0.8,
            resource_quality=0.9,
            learning_objective=0.9,
            freshness=0.7,
        )


def test_scoring_result_accepts_valid_score():

    resource_id = uuid4()

    result = RecommendationScoringResult(
        resource_id=resource_id,
        score=0.87,
        breakdown=RecommendationScoreBreakdown(
            topic_relevance=0.95,
            learning_level=0.90,
            prerequisite_compatibility=0.80,
            resource_quality=0.90,
            learning_objective=0.85,
            freshness=0.75,
        ),
        weights=RecommendationWeights(),
        algorithm_version="v1",
    )

    assert result.score == 0.87

    assert result.algorithm_version == "v1"


def test_scoring_result_rejects_negative_score():

    with pytest.raises(ValidationError):

        RecommendationScoringResult(
            resource_id=uuid4(),
            score=-0.2,
            breakdown=RecommendationScoreBreakdown(
                topic_relevance=0.5,
                learning_level=0.5,
                prerequisite_compatibility=0.5,
                resource_quality=0.5,
                learning_objective=0.5,
                freshness=0.5,
            ),
            weights=RecommendationWeights(),
            algorithm_version="v1",
        )