from app.schemas.external_resources import (
    ExternalResource,
    ExternalResourceType,
)

from app.services.educational_resources.normalization.deduplication_service import (
    ResourceDeduplicationService,
)


def create_resource(
    provider,
    external_id,
    title="Introduction to AI",
    url=None,
    metadata=None,
    description=None,
    authors=(),
    subject=None,
    language=None,
):
    return ExternalResource(
        provider=provider,
        external_id=external_id,
        title=title,
        canonical_url=url,
        resource_type=ExternalResourceType.ARTICLE,
        description=description,
        authors=authors,
        subject=subject,
        language=language,
        metadata=metadata or {},
    )


def test_deduplicates_same_provider_identity():
    first = create_resource(
        "openalex",
        "W123",
        url="https://example.com/article",
    )

    second = create_resource(
        "openalex",
        "W123",
        url="https://example.com/another-url",
    )

    result = ResourceDeduplicationService().deduplicate(
        [first, second]
    )

    assert len(result) == 1


def test_deduplicates_cross_provider_doi():
    first = create_resource(
        "openalex",
        "W123",
        url="https://openalex.org/W123",
        metadata={
            "doi": "10.1234/example.2025",
        },
    )

    second = create_resource(
        "crossref",
        "10.1234/example.2025",
        url="https://doi.org/10.1234/example.2025",
        metadata={
            "doi": "10.1234/example.2025",
        },
    )

    result = ResourceDeduplicationService().deduplicate(
        [first, second]
    )

    assert len(result) == 1

    provenance = result[0].metadata["source_provenance"]

    assert len(provenance) == 2


def test_same_title_does_not_mean_duplicate():
    first = create_resource(
        "provider-a",
        "resource-1",
        title="Introduction to AI",
        url="https://example.com/first",
    )

    second = create_resource(
        "provider-b",
        "resource-2",
        title="Introduction to AI",
        url="https://example.com/second",
    )

    result = ResourceDeduplicationService().deduplicate(
        [first, second]
    )

    assert len(result) == 2


def test_merges_descriptions_and_authors():
    first = create_resource(
        "provider-a",
        "resource-1",
        url="https://example.com/article",
        description="A detailed introduction.",
        authors=("John Smith",),
    )

    second = create_resource(
        "provider-b",
        "resource-2",
        url="https://example.com/article",
        description="",
        authors=("Jane Doe", "John Smith"),
    )

    result = ResourceDeduplicationService().deduplicate(
        [first, second]
    )

    assert len(result) == 1

    merged = result[0]

    assert merged.description == "A detailed introduction."

    assert set(merged.authors) == {
        "John Smith",
        "Jane Doe",
    }


def test_merges_metadata_without_losing_existing_provenance():
    first = create_resource(
        "provider-a",
        "resource-1",
        url="https://example.com/article",
        metadata={
            "doi": "10.1234/example.2025",
            "category": "AI",
            "source_provenance": [
                {
                    "provider": "older-provider",
                    "external_id": "old-1",
                }
            ],
        },
    )

    second = create_resource(
        "provider-b",
        "resource-2",
        url="https://example.com/article",
        metadata={
            "doi": "10.1234/example.2025",
            "description_type": "research",
        },
    )

    result = ResourceDeduplicationService().deduplicate(
        [first, second]
    )

    assert len(result) == 1

    metadata = result[0].metadata

    assert metadata["category"] == "AI"
    assert metadata["description_type"] == "research"

    provenance = metadata["source_provenance"]

    assert len(provenance) == 3


def test_deduplication_is_deterministic():
    first = create_resource(
        "provider-a",
        "resource-1",
        url="https://example.com/article",
        description="Description A",
    )

    second = create_resource(
        "provider-b",
        "resource-2",
        url="https://example.com/article",
        description="Description B",
    )

    service = ResourceDeduplicationService()

    first_result = service.deduplicate(
        [first, second]
    )

    second_result = service.deduplicate(
        [second, first]
    )

    assert first_result == second_result


def test_empty_input_returns_empty_list():
    result = ResourceDeduplicationService().deduplicate([])

    assert result == []


def test_distinct_resource_types_are_not_merged():
    article = create_resource(
        "provider-a",
        "article-1",
        url="https://example.com/resource",
    )

    video = ExternalResource(
        provider="provider-b",
        external_id="video-1",
        title="Introduction to AI",
        canonical_url="https://example.com/resource",
        resource_type=ExternalResourceType.VIDEO,
    )

    result = ResourceDeduplicationService().deduplicate(
        [article, video]
    )

    assert len(result) == 2