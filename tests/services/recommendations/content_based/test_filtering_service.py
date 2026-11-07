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
    ContentCandidateValidationError,
)

from app.services.recommendations.content_based.filtering_service import (
    ContentBasedFilteringService,
    ContentFilterCriteria,
    ContentFilteringError,
)


@pytest.fixture
def reference_id():
    return uuid4()


@pytest.fixture
def candidate(reference_id):

    resource_id = uuid4()

    features = ExtractedContentFeatures(
        resource_id=resource_id,
        title="Python Machine Learning",
        description="Learn machine learning with Python",
        subject="Computer Science",
        resource_type="tutorial",
        category_slugs=("programming", "machine-learning"),
        topics=("Python", "Machine Learning"),
        keywords=("Python", "Regression"),
        learning_objectives=("Build ML models",),
        prerequisites=("Basic Python",),
        content_format="text",
        language="English",
        difficulty="beginner",
        tokens=("python", "machine", "learning"),
    )

    breakdown = ContentSimilarityBreakdown(
        embedding_similarity=0.9,
        topic_similarity=1.0,
        keyword_similarity=1.0,
        objective_similarity=1.0,
        prerequisite_similarity=1.0,
        subject_similarity=1.0,
        content_format_similarity=1.0,
        difficulty_similarity=1.0,
        text_similarity=1.0,
    )

    score = ContentBasedScoreResult(
        reference_resource_id=reference_id,
        candidate_resource_id=resource_id,
        score=0.90,
        confidence=0.85,
        breakdown=breakdown,
        matched_topics=("python",),
        matched_keywords=("python",),
        matched_objectives=("build ml models",),
        contributing_signals=("embedding", "topics"),
    )

    return ContentBasedCandidate(
        features=features,
        scoring_result=score,
        is_active=True,
        quality_score=4.5,
    )


@pytest.fixture
def filtering_service():
    return ContentBasedFilteringService()


def test_candidate_is_accepted_by_default(
    filtering_service,
    candidate,
):

    assert filtering_service.matches(
        candidate,
        ContentFilterCriteria(),
    )


def test_inactive_candidate_is_rejected(
    filtering_service,
    candidate,
):

    inactive = replace(
        candidate,
        is_active=False,
    )

    assert not filtering_service.matches(
        inactive,
        ContentFilterCriteria(),
    )


def test_inactive_candidate_can_be_allowed(
    filtering_service,
    candidate,
):

    inactive = replace(
        candidate,
        is_active=False,
    )

    criteria = ContentFilterCriteria(
        exclude_inactive=False,
    )

    assert filtering_service.matches(
        inactive,
        criteria,
    )


def test_resource_type_filter(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        resource_types=frozenset({"tutorial"}),
    )

    assert filtering_service.matches(
        candidate,
        criteria,
    )


def test_resource_type_mismatch(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        resource_types=frozenset({"video"}),
    )

    assert not filtering_service.matches(
        candidate,
        criteria,
    )


def test_subject_filter_is_case_insensitive(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        subjects=frozenset({"computer science"}),
    )

    assert filtering_service.matches(
        candidate,
        criteria,
    )


def test_language_filter(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        languages=frozenset({"english"}),
    )

    assert filtering_service.matches(
        candidate,
        criteria,
    )


def test_difficulty_filter(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        difficulty_levels=frozenset({"beginner"}),
    )

    assert filtering_service.matches(
        candidate,
        criteria,
    )


def test_category_filter(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        categories=frozenset({"machine-learning"}),
    )

    assert filtering_service.matches(
        candidate,
        criteria,
    )


def test_category_filter_uses_any_match(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        categories=frozenset(
            {"machine-learning", "data-science"}
        ),
    )

    assert filtering_service.matches(
        candidate,
        criteria,
    )


def test_minimum_score_filter(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        minimum_score=0.95,
    )

    assert not filtering_service.matches(
        candidate,
        criteria,
    )


def test_minimum_confidence_filter(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        minimum_confidence=0.90,
    )

    assert not filtering_service.matches(
        candidate,
        criteria,
    )


def test_excluded_resource_id_filter(
    filtering_service,
    candidate,
):

    criteria = ContentFilterCriteria(
        excluded_resource_ids=frozenset(
            {candidate.resource_id}
        ),
    )

    assert not filtering_service.matches(
        candidate,
        criteria,
    )


def test_filter_returns_only_eligible_candidates(
    filtering_service,
    candidate,
):

    inactive = replace(
        candidate,
        is_active=False,
    )

    result = filtering_service.filter(
        [candidate, inactive],
    )

    assert result == [candidate]


def test_filter_preserves_scores(
    filtering_service,
    candidate,
):

    original_score = candidate.score

    filtering_service.filter([candidate])

    assert candidate.score == original_score


def test_invalid_candidate_type_is_rejected(
    filtering_service,
):

    with pytest.raises(TypeError):

        filtering_service.filter(
            ["invalid"],
        )


def test_invalid_threshold_is_rejected():

    with pytest.raises(ContentFilteringError):

        ContentFilterCriteria(
            minimum_score=1.5,
        )


def test_negative_threshold_is_rejected():

    with pytest.raises(ContentFilteringError):

        ContentFilterCriteria(
            minimum_confidence=-0.1,
        )


def test_invalid_boolean_threshold_is_rejected():

    with pytest.raises(ContentFilteringError):

        ContentFilterCriteria(
            minimum_score=True,
        )


def test_candidate_score_id_mismatch_is_rejected(
    candidate,
):

    invalid_features = replace(
        candidate.features,
        resource_id=uuid4(),
    )

    with pytest.raises(ContentCandidateValidationError):

        ContentBasedCandidate(
            features=invalid_features,
            scoring_result=candidate.scoring_result,
        )