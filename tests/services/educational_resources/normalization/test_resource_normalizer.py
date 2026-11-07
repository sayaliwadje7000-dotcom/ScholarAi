from datetime import datetime, timezone

from app.schemas.external_resources import (
    ExternalResource,
    ExternalResourceType,
    ExternalAccessType,
)

from app.services.educational_resources.normalization.resource_normalizer import (
    ExternalResourceNormalizer,
)


def create_resource():
    return ExternalResource(
        provider=" YouTube ",
        external_id=" video-123 ",
        title="  Introduction   to   AI ",
        canonical_url=(
            "https://WWW.YOUTUBE.COM/watch?v=video-123&utm_source=test"
        ),
        resource_type=ExternalResourceType.VIDEO,
        description="  An   introduction to AI. ",
        authors=(" John Smith ", "john smith", "Jane Doe"),
        subject=" Artificial Intelligence ",
        language=" EN ",
        published_at=datetime(2025, 1, 1),
        retrieved_at=datetime(2025, 1, 2),
        license="  Creative Commons ",
        access_type=ExternalAccessType.PUBLIC,
        metadata={
            "category": "  Education ",
            "details": {
                "topic": " Machine   Learning ",
            },
        },
    )


def test_normalizes_external_resource():
    resource = create_resource()

    normalizer = ExternalResourceNormalizer()

    result = normalizer.normalize(resource)

    assert result.provider == "YouTube"
    assert result.external_id == "video-123"
    assert result.title == "Introduction to AI"

    assert result.canonical_url == (
        "https://www.youtube.com/watch?v=video-123"
    )

    assert result.description == "An introduction to AI."

    assert result.authors == (
        "John Smith",
        "Jane Doe",
    )

    assert result.subject == "Artificial Intelligence"
    assert result.language == "en"
    assert result.license == "Creative Commons"

    assert result.metadata["category"] == "Education"

    assert (
        result.metadata["details"]["topic"]
        == "Machine Learning"
    )


def test_naive_dates_become_timezone_aware():
    result = ExternalResourceNormalizer().normalize(
        create_resource()
    )

    assert result.published_at.tzinfo is not None
    assert result.retrieved_at.tzinfo is not None

    assert result.published_at.utcoffset().total_seconds() == 0
    assert result.retrieved_at.utcoffset().total_seconds() == 0


def test_normalizer_does_not_mutate_original():
    original = create_resource()

    ExternalResourceNormalizer().normalize(original)

    assert original.title == "  Introduction   to   AI "
    assert original.provider == " YouTube "
    assert original.language == " EN "


def test_normalization_is_idempotent():
    normalizer = ExternalResourceNormalizer()

    first = normalizer.normalize(create_resource())
    second = normalizer.normalize(first)

    assert first == second