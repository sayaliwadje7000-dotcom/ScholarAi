from dataclasses import replace
from uuid import uuid4

import pytest

from app.services.recommendations.content_based.feature_extractor import (
    ExtractedContentFeatures,
)

from app.services.recommendations.content_based.scoring_models import (
    ContentBasedScoreResult,
    ContentSimilarityBreakdown,
)

from app.services.recommendations.content_based.candidate_models import (
    ContentBasedCandidate,
)

from app.services.recommendations.content_based.ranking_service import (
    ContentBasedRankingService,
    ContentRankingError,
)


@pytest.fixture
def reference_id():
    return uuid4()


def create_candidate(
    reference_id,
    score,
    confidence=0.8,
    quality=4.0,
    resource_id=None,
):

    resource_id = resource_id or uuid4()

    features = ExtractedContentFeatures(
        resource_id=resource_id,
        title="Machine Learning",
        description="Machine learning tutorial",
        subject="Computer Science",
        resource_type="tutorial",
        category_slugs=("machine-learning",),
        topics=("Machine Learning",),
        keywords=("Python",),
        learning_objectives=("Build models",),
        prerequisites=("Python",),
        content_format="text",
        language="English",
        difficulty="beginner",
        tokens=("machine", "learning", "python"),
    )

    breakdown = ContentSimilarityBreakdown(
        embedding_similarity=score,
        topic_similarity=score,
        keyword_similarity=score,
        objective_similarity=score,
        prerequisite_similarity=score,
        subject_similarity=score,
        content_format_similarity=score,
        difficulty_similarity=score,
        text_similarity=score,
    )

    scoring_result = ContentBasedScoreResult(
        reference_resource_id=reference_id,
        candidate_resource_id=resource_id,
        score=score,
        confidence=confidence,
        breakdown=breakdown,
        matched_topics=("machine learning",),
        matched_keywords=("python",),
        matched_objectives=("build models",),
        contributing_signals=("embedding", "topics"),
    )

    return ContentBasedCandidate(
        features=features,
        scoring_result=scoring_result,
        is_active=True,
        quality_score=quality,
    )


@pytest.fixture
def ranking_service():
    return ContentBasedRankingService()


def test_rank_returns_highest_score_first(
    ranking_service,
    reference_id,
):

    low = create_candidate(reference_id, 0.40)

    high = create_candidate(reference_id, 0.90)

    medium = create_candidate(reference_id, 0.70)

    results = ranking_service.rank(
        [low, high, medium],
    )

    assert results[0].candidate == high

    assert results[1].candidate == medium

    assert results[2].candidate == low


def test_rank_positions_start_at_one(
    ranking_service,
    reference_id,
):

    candidates = [
        create_candidate(reference_id, 0.9),
        create_candidate(reference_id, 0.7),
    ]

    results = ranking_service.rank(candidates)

    assert [
        result.rank_position
        for result in results
    ] == [1, 2]


def test_confidence_breaks_score_ties(
    ranking_service,
    reference_id,
):

    low_confidence = create_candidate(
        reference_id,
        score=0.8,
        confidence=0.4,
    )

    high_confidence = create_candidate(
        reference_id,
        score=0.8,
        confidence=0.9,
    )

    results = ranking_service.rank(
        [low_confidence, high_confidence],
    )

    assert results[0].candidate == high_confidence


def test_quality_breaks_score_and_confidence_ties(
    ranking_service,
    reference_id,
):

    low_quality = create_candidate(
        reference_id,
        score=0.8,
        confidence=0.8,
        quality=3.0,
    )

    high_quality = create_candidate(
        reference_id,
        score=0.8,
        confidence=0.8,
        quality=4.8,
    )

    results = ranking_service.rank(
        [low_quality, high_quality],
    )

    assert results[0].candidate == high_quality


def test_duplicate_resources_are_removed(
    ranking_service,
    reference_id,
):

    resource_id = uuid4()

    lower = create_candidate(
        reference_id,
        score=0.5,
        resource_id=resource_id,
    )

    higher = create_candidate(
        reference_id,
        score=0.9,
        resource_id=resource_id,
    )

    results = ranking_service.rank(
        [lower, higher],
    )

    assert len(results) == 1

    assert results[0].candidate == higher


def test_limit_is_applied_after_deduplication(
    ranking_service,
    reference_id,
):

    duplicate_id = uuid4()

    candidates = [
        create_candidate(
            reference_id,
            0.9,
            resource_id=duplicate_id,
        ),
        create_candidate(
            reference_id,
            0.8,
            resource_id=duplicate_id,
        ),
        create_candidate(reference_id, 0.7),
        create_candidate(reference_id, 0.6),
    ]

    results = ranking_service.rank(
        candidates,
        limit=2,
    )

    assert len(results) == 2


def test_empty_candidates_return_empty_list(
    ranking_service,
):

    assert ranking_service.rank([]) == []


def test_invalid_limit_zero_is_rejected(
    ranking_service,
):

    with pytest.raises(ContentRankingError):

        ranking_service.rank(
            [],
            limit=0,
        )


def test_invalid_limit_above_maximum_is_rejected(
    ranking_service,
):

    with pytest.raises(ContentRankingError):

        ranking_service.rank(
            [],
            limit=51,
        )


def test_boolean_limit_is_rejected(
    ranking_service,
):

    with pytest.raises(ContentRankingError):

        ranking_service.rank(
            [],
            limit=True,
        )


def test_invalid_candidate_type_is_rejected(
    ranking_service,
):

    with pytest.raises(TypeError):

        ranking_service.rank(
            ["invalid"],
        )


def test_different_reference_resources_are_rejected(
    ranking_service,
):

    first = create_candidate(
        uuid4(),
        0.9,
    )

    second = create_candidate(
        uuid4(),
        0.8,
    )

    with pytest.raises(ContentRankingError):

        ranking_service.rank(
            [first, second],
        )


def test_ranked_result_exposes_resource_id(
    ranking_service,
    reference_id,
):

    candidate = create_candidate(
        reference_id,
        0.9,
    )

    results = ranking_service.rank([candidate])

    assert results[0].resource_id == candidate.resource_id


def test_ranked_result_exposes_score(
    ranking_service,
    reference_id,
):

    candidate = create_candidate(
        reference_id,
        0.9,
    )

    results = ranking_service.rank([candidate])

    assert results[0].score == 0.9


def test_ranked_result_exposes_confidence(
    ranking_service,
    reference_id,
):

    candidate = create_candidate(
        reference_id,
        0.9,
        confidence=0.75,
    )

    results = ranking_service.rank([candidate])

    assert results[0].confidence == 0.75


def test_input_candidates_are_not_modified(
    ranking_service,
    reference_id,
):

    first = create_candidate(reference_id, 0.5)

    second = create_candidate(reference_id, 0.9)

    original = [first, second]

    ranking_service.rank(original)

    assert original == [first, second]