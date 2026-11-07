from uuid import uuid4

from dataclasses import replace

import pytest

from app.services.recommendations.content_based.feature_extractor import (
    ExtractedContentFeatures,
)

from app.services.recommendations.content_based.scoring_service import (
    ContentBasedScoringError,
    ContentBasedScoringService,
    ContentScoringWeights,
)


@pytest.fixture
def scoring_service():

    return ContentBasedScoringService()


@pytest.fixture
def reference_features():

    return ExtractedContentFeatures(

        resource_id=uuid4(),

        title="Python Machine Learning",

        description="Introduction to machine learning using Python",

        subject="Computer Science",

        resource_type="tutorial",

        category_slugs=("programming", "machine-learning"),

        topics=("Python", "Machine Learning", "Algorithms"),

        keywords=("Python", "Regression", "Classification"),

        learning_objectives=(
            "Understand regression",
            "Build classification models",
        ),

        prerequisites=("Basic Python",),

        content_format="text",

        language="English",

        difficulty="beginner",

        tokens=(
            "python",
            "machine",
            "learning",
            "regression",
            "classification",
        ),
    )


@pytest.fixture
def candidate_features(reference_features):

    return replace(
        reference_features,
        resource_id=uuid4(),
    )


def test_identical_features_produce_high_similarity(
    scoring_service,
    reference_features,
    candidate_features,
):

    result = scoring_service.score(
        reference_features,
        candidate_features,
        embedding_similarity=1.0,
    )

    assert result.score == 1.0

    assert result.confidence == 1.0


def test_identical_resource_id_is_supported(
    scoring_service,
    reference_features,
):

    result = scoring_service.score(
        reference_features,
        reference_features,
        embedding_similarity=1.0,
    )

    assert result.score == 1.0


def test_embedding_similarity_is_normalized(
    scoring_service,
    reference_features,
    candidate_features,
):

    result = scoring_service.score(
        reference_features,
        candidate_features,
        embedding_similarity=0.0,
    )

    assert result.breakdown.embedding_similarity == 0.5


def test_negative_embedding_similarity_is_normalized(
    scoring_service,
    reference_features,
    candidate_features,
):

    result = scoring_service.score(
        reference_features,
        candidate_features,
        embedding_similarity=-1.0,
    )

    assert result.breakdown.embedding_similarity == 0.0


@pytest.mark.parametrize(
    "value",
    [
        -1.1,
        1.1,
        float("nan"),
        float("inf"),
        True,
        "0.5",
    ],
)
def test_invalid_embedding_similarity_is_rejected(
    scoring_service,
    reference_features,
    candidate_features,
    value,
):

    with pytest.raises(ContentBasedScoringError):

        scoring_service.score(
            reference_features,
            candidate_features,
            embedding_similarity=value,
        )


def test_missing_embedding_similarity_does_not_fail(
    scoring_service,
    reference_features,
    candidate_features,
):

    result = scoring_service.score(
        reference_features,
        candidate_features,
    )

    assert result.score == pytest.approx(1.0)

    assert "embedding" not in result.contributing_signals


def test_topic_similarity_uses_jaccard(
    scoring_service,
    reference_features,
    candidate_features,
):

    reference = replace(
        reference_features,
        topics=("Python", "Machine Learning"),
    )

    candidate = replace(
        candidate_features,
        topics=("Python", "Deep Learning"),
    )

    result = scoring_service.score(
        reference,
        candidate,
    )

    assert result.breakdown.topic_similarity == pytest.approx(
        1 / 3
    )


def test_topic_matching_is_case_insensitive(
    scoring_service,
    reference_features,
    candidate_features,
):

    reference = replace(
        reference_features,
        topics=("Python",),
    )

    candidate = replace(
        candidate_features,
        topics=("python",),
    )

    result = scoring_service.score(
        reference,
        candidate,
    )

    assert result.matched_topics == ("python",)

    assert result.breakdown.topic_similarity == 1.0


def test_matched_keywords_are_returned(
    scoring_service,
    reference_features,
    candidate_features,
):

    result = scoring_service.score(
        reference_features,
        candidate_features,
    )

    assert "classification" in result.matched_keywords

    assert "python" in result.matched_keywords


def test_matched_objectives_are_returned(
    scoring_service,
    reference_features,
    candidate_features,
):

    result = scoring_service.score(
        reference_features,
        candidate_features,
    )

    assert len(result.matched_objectives) == 2


def test_subject_similarity(
    scoring_service,
    reference_features,
    candidate_features,
):

    result = scoring_service.score(
        reference_features,
        candidate_features,
    )

    assert result.breakdown.subject_similarity == 1.0


def test_different_subjects_have_zero_similarity(
    scoring_service,
    reference_features,
    candidate_features,
):

    candidate = replace(
        candidate_features,
        subject="Physics",
    )

    result = scoring_service.score(
        reference_features,
        candidate,
    )

    assert result.breakdown.subject_similarity == 0.0


def test_difficulty_similarity(
    scoring_service,
    reference_features,
    candidate_features,
):

    candidate = replace(
        candidate_features,
        difficulty="intermediate",
    )

    result = scoring_service.score(
        reference_features,
        candidate,
    )

    assert result.breakdown.difficulty_similarity == 0.5


def test_missing_features_are_excluded_from_weighting(
    scoring_service,
    reference_features,
    candidate_features,
):

    reference = replace(
        reference_features,
        topics=(),
        keywords=(),
        learning_objectives=(),
        prerequisites=(),
        subject="",
        content_format="",
        difficulty="",
        tokens=(),
    )

    candidate = replace(
        candidate_features,
        topics=(),
        keywords=(),
        learning_objectives=(),
        prerequisites=(),
        subject="",
        content_format="",
        difficulty="",
        tokens=(),
    )

    result = scoring_service.score(
        reference,
        candidate,
    )

    assert result.score == 0.0

    assert result.confidence == 0.0


def test_score_stays_between_zero_and_one(
    scoring_service,
    reference_features,
    candidate_features,
):

    result = scoring_service.score(
        reference_features,
        candidate_features,
        embedding_similarity=0.8,
    )

    assert 0.0 <= result.score <= 1.0


def test_confidence_stays_between_zero_and_one(
    scoring_service,
    reference_features,
    candidate_features,
):

    result = scoring_service.score(
        reference_features,
        candidate_features,
        embedding_similarity=0.8,
    )

    assert 0.0 <= result.confidence <= 1.0


def test_invalid_reference_type_is_rejected(
    scoring_service,
    candidate_features,
):

    with pytest.raises(ContentBasedScoringError):

        scoring_service.score(
            reference="invalid",
            candidate=candidate_features,
        )


def test_invalid_candidate_type_is_rejected(
    scoring_service,
    reference_features,
):

    with pytest.raises(ContentBasedScoringError):

        scoring_service.score(
            reference=reference_features,
            candidate="invalid",
        )


def test_custom_weights_are_supported(
    reference_features,
    candidate_features,
):

    weights = ContentScoringWeights(
        embedding=1.0,
        topics=0.0,
        keywords=0.0,
        objectives=0.0,
        prerequisites=0.0,
        subject=0.0,
        content_format=0.0,
        difficulty=0.0,
        text=0.0,
    )

    service = ContentBasedScoringService(
        weights=weights,
    )

    result = service.score(
        reference_features,
        candidate_features,
        embedding_similarity=0.5,
    )

    assert result.score == 0.75


def test_invalid_negative_weights_are_rejected():

    with pytest.raises(ContentBasedScoringError):

        ContentScoringWeights(
            embedding=-1.0,
        )


def test_all_zero_weights_are_rejected():

    with pytest.raises(ContentBasedScoringError):

        ContentScoringWeights(
            embedding=0.0,
            topics=0.0,
            keywords=0.0,
            objectives=0.0,
            prerequisites=0.0,
            subject=0.0,
            content_format=0.0,
            difficulty=0.0,
            text=0.0,
        )