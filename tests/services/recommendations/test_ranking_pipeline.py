from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.recommendations import (
    RecommendationRequest,
    RecommendationScoreBreakdown,
    RecommendationScoringResult,
    RecommendationWeights,
)

from app.schemas.resource_metadata import (
    ResourceClassification,
)

from app.services.recommendations.filtering_service import (
    RecommendationFilteringService,
)

from app.services.recommendations.ranking_service import (
    RecommendationRankingService,
)

from app.services.recommendations.ranking_pipeline import (
    RecommendationRankingPipeline,
)


@pytest.fixture
def filtering_service():
    return RecommendationFilteringService()


@pytest.fixture
def ranking_service():
    return RecommendationRankingService()


@pytest.fixture
def pipeline():
    return RecommendationRankingPipeline()


def make_candidate(
    *,
    score=0.8,
    quality=4.0,
    resource_type="video",
    language="english",
    subject="Data Structures",
    difficulty="beginner",
    active=True,
    resource_id=None,
):
    resource_id = resource_id or uuid4()

    resource = ResourceClassification(
        resource_id=str(resource_id),
        title="Test Resource",
        resource_type=resource_type,
        subject=subject,
        difficulty=difficulty,
        language=language,
        category_slugs=[],
        topics=[],
        keywords=[],
        learning_objectives=[],
        prerequisites=[],
        content_format=resource_type,
        quality_score=quality,
        published_at=datetime.now(timezone.utc),
        is_active=active,
    )

    breakdown = RecommendationScoreBreakdown(
        topic_relevance=score,
        learning_level=score,
        prerequisite_compatibility=score,
        resource_quality=score,
        learning_objective=score,
        freshness=score,
    )

    scoring_result = RecommendationScoringResult(
        resource_id=resource_id,
        score=score,
        breakdown=breakdown,
        weights=RecommendationWeights(),
        algorithm_version="rule-based-v1",
    )

    return resource, scoring_result


def test_filtering_keeps_matching_resource(filtering_service):
    candidate = make_candidate()

    result = filtering_service.filter(
        [candidate],
        RecommendationRequest(),
    )

    assert result == [candidate]


def test_filtering_excludes_inactive_resource(filtering_service):
    candidate = make_candidate(active=False)

    result = filtering_service.filter(
        [candidate],
        RecommendationRequest(),
    )

    assert result == []


def test_filtering_by_resource_type(filtering_service):
    video = make_candidate(resource_type="video")
    article = make_candidate(resource_type="article")

    request = RecommendationRequest(
        resource_types=["video"]
    )

    result = filtering_service.filter(
        [video, article],
        request,
    )

    assert result == [video]


def test_filtering_by_language(filtering_service):
    english = make_candidate(language="english")
    hindi = make_candidate(language="hindi")

    result = filtering_service.filter(
        [english, hindi],
        RecommendationRequest(language="english"),
    )

    assert result == [english]


def test_filtering_by_subject(filtering_service):
    matching = make_candidate(subject="Data Structures")
    other = make_candidate(subject="Operating Systems")

    result = filtering_service.filter(
        [matching, other],
        RecommendationRequest(subject="Data Structures"),
    )

    assert result == [matching]


def test_filtering_by_difficulty(filtering_service):
    beginner = make_candidate(difficulty="beginner")
    advanced = make_candidate(difficulty="advanced")

    result = filtering_service.filter(
        [beginner, advanced],
        RecommendationRequest(difficulty_level="beginner"),
    )

    assert result == [beginner]


def test_filtering_excludes_completed_resources(filtering_service):
    candidate = make_candidate()
    resource, _ = candidate

    class Interaction:
        resource_id = resource.resource_id
        interaction_type = "complete"

    result = filtering_service.filter(
        [candidate],
        RecommendationRequest(exclude_completed=True),
        interactions=[Interaction()],
    )

    assert result == []


def test_filtering_can_include_completed_resources(filtering_service):
    candidate = make_candidate()
    resource, _ = candidate

    class Interaction:
        resource_id = resource.resource_id
        interaction_type = "complete"

    result = filtering_service.filter(
        [candidate],
        RecommendationRequest(exclude_completed=False),
        interactions=[Interaction()],
    )

    assert result == [candidate]


def test_ranking_orders_by_score_descending(ranking_service):
    low = make_candidate(score=0.3)
    high = make_candidate(score=0.9)
    medium = make_candidate(score=0.6)

    result = ranking_service.rank(
        [low, high, medium],
    )

    assert [item.score for item in result] == [
        pytest.approx(0.9),
        pytest.approx(0.6),
        pytest.approx(0.3),
    ]


def test_ranking_tiebreaks_by_quality(ranking_service):
    low_quality = make_candidate(
        score=0.8,
        quality=3.0,
    )

    high_quality = make_candidate(
        score=0.8,
        quality=5.0,
    )

    result = ranking_service.rank(
        [low_quality, high_quality],
    )

    assert result[0].resource.quality_score == 5.0


def test_ranking_tiebreaks_by_resource_id(ranking_service):
    first_id = uuid4()
    second_id = uuid4()

    first = make_candidate(
        resource_id=first_id,
        score=0.8,
        quality=4.0,
    )

    second = make_candidate(
        resource_id=second_id,
        score=0.8,
        quality=4.0,
    )

    result = ranking_service.rank(
        [first, second],
    )

    expected = sorted(
        [first_id, second_id],
        key=str,
    )

    assert [item.resource_id for item in result] == expected


def test_ranking_removes_duplicates(ranking_service):
    resource_id = uuid4()

    low = make_candidate(
        resource_id=resource_id,
        score=0.4,
    )

    high = make_candidate(
        resource_id=resource_id,
        score=0.9,
    )

    result = ranking_service.rank(
        [low, high],
    )

    assert len(result) == 1
    assert result[0].score == pytest.approx(0.9)


def test_ranking_assigns_consecutive_positions(ranking_service):
    candidates = [
        make_candidate(score=0.2),
        make_candidate(score=0.8),
        make_candidate(score=0.5),
    ]

    result = ranking_service.rank(candidates)

    assert [item.rank_position for item in result] == [
        1,
        2,
        3,
    ]


def test_ranking_applies_limit_after_deduplication(ranking_service):
    shared_id = uuid4()

    candidates = [
        make_candidate(resource_id=shared_id, score=0.9),
        make_candidate(resource_id=shared_id, score=0.8),
        make_candidate(score=0.7),
    ]

    result = ranking_service.rank(
        candidates,
        limit=2,
    )

    assert len(result) == 2
    assert result[0].score == pytest.approx(0.9)
    assert result[1].score == pytest.approx(0.7)


def test_ranking_rejects_invalid_limit(ranking_service):
    with pytest.raises(ValueError):
        ranking_service.rank([], limit=0)

    with pytest.raises(ValueError):
        ranking_service.rank([], limit=51)

    with pytest.raises(TypeError):
        ranking_service.rank([], limit=True)


def test_ranking_rejects_mismatched_resource_id(ranking_service):
    resource, scoring_result = make_candidate()

    resource.resource_id = str(uuid4())

    with pytest.raises(ValueError):
        ranking_service.rank([
            (resource, scoring_result)
        ])


def test_pipeline_filters_before_ranking(pipeline):
    matching = make_candidate(
        score=0.7,
        language="english",
    )

    excluded = make_candidate(
        score=0.9,
        language="hindi",
    )

    result = pipeline.execute(
        [excluded, matching],
        RecommendationRequest(
            language="english",
            limit=10,
        ),
    )

    assert len(result) == 1
    assert result[0].score == pytest.approx(0.7)


def test_pipeline_is_deterministic(pipeline):
    candidates = [
        make_candidate(score=0.7),
        make_candidate(score=0.9),
        make_candidate(score=0.8),
    ]

    request = RecommendationRequest()

    first = pipeline.execute(candidates, request)
    second = pipeline.execute(candidates, request)

    assert [
        item.resource_id for item in first
    ] == [
        item.resource_id for item in second
    ]


def test_pipeline_preserves_scoring_metadata(pipeline):
    candidate = make_candidate(score=0.85)

    result = pipeline.execute(
        [candidate],
        RecommendationRequest(),
    )

    assert len(result) == 1

    assert (
        result[0].algorithm_version
        == "rule-based-v1"
    )

    assert (
        result[0].scoring_result.breakdown
        == candidate[1].breakdown
    )