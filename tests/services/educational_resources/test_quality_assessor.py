from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.external_resources import (
    ExternalAccessType,
    ExternalResource,
    ExternalResourceType,
)

from app.services.educational_resources.quality_assessor import (
    FreshnessPolicy,
    QualityWeights,
    ResourceQualityAssessor,
)


FIXED_NOW = datetime(
    2026,
    11,
    7,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


def create_resource(
    *,
    provider: str = "openalex",
    external_id: str = "resource-1",
    title: str = "Introduction to Machine Learning",
    description: str | None = (
        "A comprehensive introduction to machine learning."
    ),
    authors: tuple[str, ...] = ("Author One",),
    subject: str | None = "Computer Science",
    language: str | None = "en",
    published_at: datetime | None = FIXED_NOW
    - timedelta(days=30),
    license: str | None = "CC BY 4.0",
    access_type: ExternalAccessType = (
        ExternalAccessType.OPEN_ACCESS
    ),
    resource_type: ExternalResourceType = (
        ExternalResourceType.ARTICLE
    ),
    metadata: dict | None = None,
) -> ExternalResource:

    return ExternalResource(
        provider=provider,
        external_id=external_id,
        title=title,
        canonical_url=(
            f"https://example.com/{external_id}"
        ),
        resource_type=resource_type,
        description=description,
        authors=authors,
        subject=subject,
        language=language,
        published_at=published_at,
        retrieved_at=FIXED_NOW,
        license=license,
        access_type=access_type,
        metadata=metadata or {},
    )


@pytest.fixture
def assessor():
    return ResourceQualityAssessor(
        clock=lambda: FIXED_NOW
    )


# ---------------------------------------------------------
# Configuration tests
# ---------------------------------------------------------


def test_default_weights_sum_to_one():

    weights = QualityWeights()

    assert (
        weights.completeness
        + weights.credibility
        + weights.freshness
    ) == pytest.approx(1.0)


def test_rejects_weights_that_do_not_sum_to_one():

    with pytest.raises(ValueError):
        QualityWeights(
            completeness=0.50,
            credibility=0.30,
            freshness=0.30,
        )


def test_rejects_negative_weights():

    with pytest.raises(ValueError):
        QualityWeights(
            completeness=-0.10,
            credibility=0.60,
            freshness=0.50,
        )


def test_rejects_invalid_provider_credibility():

    with pytest.raises(ValueError):
        ResourceQualityAssessor(
            provider_credibility={
                "openalex": 1.5,
            }
        )


def test_rejects_invalid_unknown_provider_score():

    with pytest.raises(ValueError):
        ResourceQualityAssessor(
            unknown_provider_score=-0.1
        )


def test_rejects_invalid_freshness_policy():

    with pytest.raises(ValueError):
        FreshnessPolicy(
            half_life_days={
                "article": 0,
            }
        )


# ---------------------------------------------------------
# Metadata completeness tests
# ---------------------------------------------------------


def test_complete_resource_has_full_completeness_score(
    assessor,
):

    resource = create_resource()

    result = assessor.assess(resource)

    assert result.completeness_score == 100.0


def test_missing_metadata_reduces_completeness_score(
    assessor,
):

    resource = create_resource(
        description=None,
        authors=(),
        subject=None,
        language=None,
        published_at=None,
        license=None,
        access_type=ExternalAccessType.UNKNOWN,
    )

    result = assessor.assess(resource)

    assert result.completeness_score < 100.0


def test_missing_description_costs_twenty_points(
    assessor,
):

    resource = create_resource(
        description=None,
    )

    result = assessor.assess(resource)

    assert result.completeness_score == 80.0


# ---------------------------------------------------------
# Provider credibility tests
# ---------------------------------------------------------


def test_known_provider_uses_configured_credibility(
    assessor,
):

    resource = create_resource(
        provider="openalex",
    )

    result = assessor.assess(resource)

    assert result.credibility_score == 90.0


def test_provider_lookup_is_case_insensitive(
    assessor,
):

    resource = create_resource(
        provider="OpenAlex",
    )

    result = assessor.assess(resource)

    assert result.credibility_score == 90.0


def test_unknown_provider_receives_neutral_score(
    assessor,
):

    resource = create_resource(
        provider="unknown_provider",
    )

    result = assessor.assess(resource)

    assert result.credibility_score == 50.0

    assert "unknown_provider" in result.flags


# ---------------------------------------------------------
# Freshness tests
# ---------------------------------------------------------


def test_recent_resource_has_high_freshness_score(
    assessor,
):

    resource = create_resource(
        published_at=FIXED_NOW - timedelta(days=1),
    )

    result = assessor.assess(resource)

    assert result.freshness_score > 99.0


def test_resource_at_half_life_has_fifty_freshness_score():

    assessor = ResourceQualityAssessor(
        clock=lambda: FIXED_NOW,
        freshness_policy=FreshnessPolicy(
            half_life_days={
                "article": 100,
            }
        ),
    )

    resource = create_resource(
        published_at=FIXED_NOW - timedelta(days=100),
    )

    result = assessor.assess(resource)

    assert result.freshness_score == pytest.approx(
        50.0,
        abs=0.01,
    )


def test_older_resource_has_lower_freshness_score():

    assessor = ResourceQualityAssessor(
        clock=lambda: FIXED_NOW,
    )

    recent = create_resource(
        external_id="recent",
        published_at=FIXED_NOW - timedelta(days=30),
    )

    old = create_resource(
        external_id="old",
        published_at=FIXED_NOW - timedelta(days=1500),
    )

    recent_result = assessor.assess(recent)
    old_result = assessor.assess(old)

    assert (
        recent_result.freshness_score
        > old_result.freshness_score
    )


def test_missing_publication_date_receives_neutral_score(
    assessor,
):

    resource = create_resource(
        published_at=None,
    )

    result = assessor.assess(resource)

    assert result.freshness_score == 50.0

    assert "publication_date_missing" in result.flags


def test_future_publication_date_is_flagged(
    assessor,
):

    resource = create_resource(
        published_at=FIXED_NOW + timedelta(days=30),
    )

    result = assessor.assess(resource)

    assert result.freshness_score == 50.0

    assert "future_publication_date" in result.flags


def test_naive_publication_date_is_handled_as_utc(
    assessor,
):

    resource = create_resource(
        published_at=datetime(2026, 11, 6, 12, 0, 0),
    )

    result = assessor.assess(resource)

    assert result.freshness_score > 99.0


# ---------------------------------------------------------
# Overall score tests
# ---------------------------------------------------------


def test_overall_score_uses_configured_weights():

    assessor = ResourceQualityAssessor(
        clock=lambda: FIXED_NOW,
        weights=QualityWeights(
            completeness=0.50,
            credibility=0.30,
            freshness=0.20,
        ),
        provider_credibility={
            "openalex": 1.0,
        },
    )

    resource = create_resource(
        description=None,
        published_at=None,
    )

    result = assessor.assess(resource)

    expected = (
        result.completeness_score * 0.50
        + result.credibility_score * 0.30
        + result.freshness_score * 0.20
    )

    assert result.overall_score == round(
        expected,
        2,
    )


def test_all_scores_remain_between_zero_and_one_hundred(
    assessor,
):

    resource = create_resource(
        published_at=FIXED_NOW - timedelta(days=10000),
    )

    result = assessor.assess(resource)

    assert 0 <= result.overall_score <= 100
    assert 0 <= result.completeness_score <= 100
    assert 0 <= result.credibility_score <= 100
    assert 0 <= result.freshness_score <= 100


# ---------------------------------------------------------
# Resource enrichment tests
# ---------------------------------------------------------


def test_assess_resource_adds_quality_metadata(
    assessor,
):

    resource = create_resource()

    enriched = assessor.assess_resource(resource)

    assert "quality_assessment" in enriched.metadata

    quality = enriched.metadata["quality_assessment"]

    assert quality["algorithm_version"] == "1.0.0"

    assert 0 <= quality["overall_score"] <= 100


def test_assess_resource_preserves_existing_metadata(
    assessor,
):

    resource = create_resource(
        metadata={
            "provider_metadata": {
                "category": "research",
            },
            "source_provenance": [
                {
                    "provider": "openalex",
                    "external_id": "resource-1",
                }
            ],
        }
    )

    enriched = assessor.assess_resource(resource)

    assert enriched.metadata["provider_metadata"] == {
        "category": "research",
    }

    assert enriched.metadata["source_provenance"] == [
        {
            "provider": "openalex",
            "external_id": "resource-1",
        }
    ]


def test_assess_resource_does_not_mutate_original(
    assessor,
):

    resource = create_resource(
        metadata={
            "existing": "value",
        }
    )

    original_metadata = dict(resource.metadata)

    enriched = assessor.assess_resource(resource)

    assert resource.metadata == original_metadata

    assert "quality_assessment" not in resource.metadata

    assert "quality_assessment" in enriched.metadata


def test_assess_many_preserves_resource_order(
    assessor,
):

    first = create_resource(
        external_id="first",
    )

    second = create_resource(
        external_id="second",
    )

    third = create_resource(
        external_id="third",
    )

    results = assessor.assess_many(
        [first, second, third]
    )

    assert [
        resource.external_id
        for resource in results
    ] == [
        "first",
        "second",
        "third",
    ]


def test_assess_many_rejects_non_list():

    assessor = ResourceQualityAssessor(
        clock=lambda: FIXED_NOW
    )

    with pytest.raises(TypeError):
        assessor.assess_many(
            (create_resource(),)
        )


def test_assess_rejects_invalid_resource():

    assessor = ResourceQualityAssessor(
        clock=lambda: FIXED_NOW
    )

    with pytest.raises(TypeError):
        assessor.assess("invalid")


def test_assessment_serialization_is_json_compatible(
    assessor,
):

    resource = create_resource()

    result = assessor.assess(resource)

    data = result.to_dict()

    assert isinstance(data, dict)

    assert isinstance(
        data["evaluated_at"],
        str,
    )

    assert isinstance(
        data["flags"],
        list,
    )

    assert data["algorithm_version"] == "1.0.0"