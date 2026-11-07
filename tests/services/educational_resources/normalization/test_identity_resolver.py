from app.schemas.external_resources import (
    ExternalResource,
    ExternalResourceType,
)

from app.services.educational_resources.normalization.identity_resolver import (
    ResourceIdentityResolver,
)


def create_resource(
    provider="openalex",
    external_id="W123456",
    url="https://example.com/article",
    metadata=None,
):
    return ExternalResource(
        provider=provider,
        external_id=external_id,
        title="Research Article",
        canonical_url=url,
        resource_type=ExternalResourceType.ARTICLE,
        metadata=metadata or {},
    )


def test_resolves_provider_identity():
    resource = create_resource()

    identities = ResourceIdentityResolver().resolve(resource)

    assert (
        "type:article:provider:openalex:W123456"
        in identities
    )


def test_resolves_doi_from_metadata():
    resource = create_resource(
        metadata={
            "doi": "10.1234/example.2025",
        }
    )

    identities = ResourceIdentityResolver().resolve(resource)

    assert (
        "type:article:doi:10.1234/example.2025"
        in identities
    )


def test_resolves_doi_url():
    resource = create_resource(
        metadata={
            "doi": "https://doi.org/10.1234/example.2025",
        }
    )

    identities = ResourceIdentityResolver().resolve(resource)

    assert (
        "type:article:doi:10.1234/example.2025"
        in identities
    )


def test_resolves_nested_doi():
    resource = create_resource(
        metadata={
            "publication": {
                "identifiers": {
                    "doi": "10.1234/nested.2025",
                }
            }
        }
    )

    identities = ResourceIdentityResolver().resolve(resource)

    assert (
        "type:article:doi:10.1234/nested.2025"
        in identities
    )


def test_resolves_canonical_url():
    resource = create_resource(
        url="https://example.com/article?utm_source=test"
    )

    identities = ResourceIdentityResolver().resolve(resource)

    assert (
        "type:article:url:https://example.com/article"
        in identities
    )


def test_title_is_not_an_identity():
    first = create_resource(
        provider="provider-a",
        external_id="1",
        url="https://example.com/first-article",
    )

    second = create_resource(
        provider="provider-b",
        external_id="2",
        url="https://example.com/second-article",
    )

    resolver = ResourceIdentityResolver()

    first_identities = resolver.resolve(first)
    second_identities = resolver.resolve(second)

    assert first_identities.isdisjoint(second_identities)

def test_resource_types_are_part_of_identity():
    article = create_resource(
        url="https://example.com/resource"
    )

    video = ExternalResource(
        provider="youtube",
        external_id="video-1",
        title="Research Article",
        canonical_url="https://example.com/resource",
        resource_type=ExternalResourceType.VIDEO,
    )

    resolver = ResourceIdentityResolver()

    assert resolver.resolve(article).isdisjoint(
        resolver.resolve(video)
    )