from datetime import datetime, timezone

import pytest

from app.schemas.external_resources import (
    ExternalAccessType,
    ExternalResource,
    ExternalResourceType,
)

from app.services.educational_resources.relevance_ranker import (
    RelevanceWeights,
    ResourceRelevanceRanker,
)


@pytest.fixture
def ranker():

    return ResourceRelevanceRanker()


def make_resource(
    *,
    title="Binary Search Tree",
    description="Learn binary search tree concepts.",
    subject="Data Structures",
    authors=("Computer Science",),
    metadata=None,
    external_id="resource-1",
):

    return ExternalResource(
        provider="openalex",
        external_id=external_id,
        title=title,
        canonical_url=(
            f"https://example.com/{external_id}"
        ),
        resource_type=ExternalResourceType.ARTICLE,
        description=description,
        authors=authors,
        subject=subject,
        language="en",
        published_at=None,
        retrieved_at=datetime.now(timezone.utc),
        license="Open Access",
        access_type=ExternalAccessType.OPEN_ACCESS,
        metadata=metadata or {},
    )


# ---------------------------------------------------------
# Weight validation
# ---------------------------------------------------------

def test_default_weights_total_one_hundred():

    weights = RelevanceWeights()

    assert (
        weights.title_phrase
        + weights.title
        + weights.subject
        + weights.description
        + weights.metadata
        + weights.authors
    ) == 100.0


def test_rejects_invalid_weight_total():

    with pytest.raises(ValueError):

        RelevanceWeights(
            title_phrase=20,
            title=20,
            subject=10,
            description=10,
            metadata=10,
            authors=5,
        )


def test_rejects_negative_weights():

    with pytest.raises(ValueError):

        RelevanceWeights(
            title_phrase=-1,
            title=26,
            subject=15,
            description=15,
            metadata=10,
            authors=5,
        )


# ---------------------------------------------------------
# Text normalization
# ---------------------------------------------------------

def test_normalizes_case_and_punctuation(ranker):

    assert (
        ranker._normalize_text(
            "Binary-Search, TREE!"
        )
        == "binary search tree"
    )


def test_removes_common_stop_words(ranker):

    terms = ranker._tokenize(
        "How to learn binary search trees"
    )

    assert terms == (
        "learn",
        "binary",
        "search",
        "trees",
    )


def test_empty_query_has_zero_score(ranker):

    resource = make_resource()

    result = ranker.assess(
        resource,
        "the and or",
    )

    assert result.score == 0.0

    assert result.matched_terms == ()


# ---------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------

def test_exact_title_phrase_receives_bonus(ranker):

    resource = make_resource(
        title="Binary Search Tree Deletion",
    )

    result = ranker.assess(
        resource,
        "binary search tree deletion",
    )

    assert result.score > 30.0

    assert (
        "title_phrase"
        in result.matched_fields
    )


def test_title_match_scores_higher_than_description_only(
    ranker,
):

    title_match = make_resource(
        title="Binary Search Tree Deletion",
        description="",
        subject=None,
        authors=(),
    )

    description_match = make_resource(
        title="Computer Science",
        description=(
            "Binary search tree deletion tutorial"
        ),
        subject=None,
        authors=(),
    )

    first = ranker.assess(
        title_match,
        "binary search tree deletion",
    )

    second = ranker.assess(
        description_match,
        "binary search tree deletion",
    )

    assert first.score > second.score


def test_subject_match_contributes_to_score(ranker):

    resource = make_resource(
        title="Algorithms",
        description="",
        subject="Binary Search Tree",
        authors=(),
    )

    result = ranker.assess(
        resource,
        "binary search tree",
    )

    assert "subject" in result.matched_fields

    assert result.score > 0


def test_metadata_keywords_contribute_to_score(ranker):

    resource = make_resource(
        title="Algorithms",
        description="",
        subject=None,
        authors=(),
        metadata={
            "topics": [
                "Binary Search Tree",
            ],
            "keywords": [
                "tree deletion",
            ],
        },
    )

    result = ranker.assess(
        resource,
        "binary search tree deletion",
    )

    assert "metadata" in result.matched_fields

    assert result.score > 0


def test_matched_terms_are_unique(ranker):

    resource = make_resource(
        title="Binary Binary Search Tree",
        description="Binary search tree",
    )

    result = ranker.assess(
        resource,
        "binary binary search tree",
    )

    assert len(
        result.matched_terms
    ) == len(
        set(result.matched_terms)
    )


def test_score_is_within_zero_and_one_hundred(ranker):

    resource = make_resource()

    result = ranker.assess(
        resource,
        "binary search tree",
    )

    assert 0 <= result.score <= 100


# ---------------------------------------------------------
# Assessment metadata
# ---------------------------------------------------------

def test_assessment_is_attached_to_resource(ranker):

    resource = make_resource()

    assessed = ranker.assess_resource(
        resource,
        "binary search tree",
    )

    assert (
        "relevance_assessment"
        in assessed.metadata
    )

    assert (
        assessed.metadata[
            "relevance_assessment"
        ]["score"]
        >= 0
    )


def test_original_resource_metadata_is_not_mutated(
    ranker,
):

    resource = make_resource()

    original_metadata = dict(
        resource.metadata
    )

    ranker.assess_resource(
        resource,
        "binary search tree",
    )

    assert resource.metadata == original_metadata


def test_assessment_contains_algorithm_version(
    ranker,
):

    resource = make_resource()

    result = ranker.assess(
        resource,
        "binary search tree",
    )

    assert result.algorithm_version == "1.0.0"


# ---------------------------------------------------------
# Ranking
# ---------------------------------------------------------

def test_rank_places_more_relevant_resource_first(
    ranker,
):

    general = make_resource(
        title="Introduction to Computer Science",
        description="General computer science concepts.",
        subject="Computer Science",
        external_id="general",
    )

    specific = make_resource(
        title="Binary Search Tree Deletion",
        description=(
            "Detailed explanation of deleting "
            "nodes from a binary search tree."
        ),
        subject="Data Structures",
        external_id="specific",
    )

    ranked = ranker.rank(
        [
            general,
            specific,
        ],
        "binary search tree deletion",
    )

    assert ranked[0].external_id == "specific"


def test_rank_is_deterministic(ranker):

    resources = [
        make_resource(
            title="Binary Search Tree",
            external_id="b",
        ),
        make_resource(
            title="Binary Search Tree",
            external_id="a",
        ),
    ]

    first = ranker.rank(
        resources,
        "binary search tree",
    )

    second = ranker.rank(
        resources,
        "binary search tree",
    )

    assert [
        resource.external_id
        for resource in first
    ] == [
        resource.external_id
        for resource in second
    ]


def test_rank_does_not_mutate_input_list(ranker):

    resources = [
        make_resource(
            external_id="b",
        ),
        make_resource(
            external_id="a",
        ),
    ]

    original_order = [
        resource.external_id
        for resource in resources
    ]

    ranker.rank(
        resources,
        "binary search tree",
    )

    assert [
        resource.external_id
        for resource in resources
    ] == original_order


def test_rank_rejects_non_list():

    ranker = ResourceRelevanceRanker()

    with pytest.raises(TypeError):

        ranker.rank(
            (),
            "binary search tree",
        )