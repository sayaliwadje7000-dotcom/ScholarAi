from datetime import datetime, timezone

from unittest.mock import AsyncMock

import pytest

from app.schemas.educational_resource_discovery import (
    ResourceDiscoveryRequest,
)

from app.schemas.external_resources import (
    ExternalAccessType,
    ExternalResource,
    ExternalResourceType,
)

from app.services.educational_resources.discovery_service import (
    ResourceDiscoveryService,
)

from app.services.educational_resources.discovery_exceptions import (
    ResourceDiscoveryUnavailableError,
    ResourceDiscoveryValidationError,
)


class FakeProvider:

    def __init__(
        self,
        name,
        results=None,
        error=None,
    ):

        self.name = name

        self.results = results or []

        self.error = error

        self.search = AsyncMock(
            side_effect=self._search
        )

    async def _search(
        self,
        query,
        limit,
    ):

        if self.error:
            raise self.error

        return self.results


class FakeRegistry:

    def __init__(self, providers):

        self.providers = providers

    def list(self):
        return list(self.providers.keys())

    def get(self, name):
        return self.providers.get(name)


@pytest.fixture
def sample_resource():

    return ExternalResource(
        provider="openalex",
        external_id="W123456",
        title="Introduction to Machine Learning",
        canonical_url="https://example.com/ml",
        resource_type=ExternalResourceType.ARTICLE,
        description="Machine learning fundamentals.",
        authors=("Author One",),
        subject="Computer Science",
        language="en",
        published_at=datetime(
            2025,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        retrieved_at=datetime.now(timezone.utc),
        license="CC BY 4.0",
        access_type=ExternalAccessType.OPEN_ACCESS,
        metadata={
            "topics": ["machine learning"],
        },
    )


@pytest.fixture
def registry(sample_resource):

    youtube_resource = ExternalResource(
        provider="youtube",
        external_id="video123",
        title="Machine Learning Video",
        canonical_url="https://www.youtube.com/watch?v=video123",
        resource_type=ExternalResourceType.VIDEO,
        description="Video about machine learning.",
        authors=(),
        subject="Computer Science",
        language="en",
        published_at=None,
        retrieved_at=datetime.now(timezone.utc),
        license=None,
        access_type=ExternalAccessType.PUBLIC,
        metadata={},
    )

    return FakeRegistry(
        {
            "openalex": FakeProvider(
                "openalex",
                [sample_resource],
            ),
            "youtube": FakeProvider(
                "youtube",
                [youtube_resource],
            ),
        }
    )


@pytest.fixture
def discovery_service(registry):

    return ResourceDiscoveryService(
        registry=registry,
        max_concurrent_providers=2,
    )


def test_discovery_returns_standardized_response(
    discovery_service,
):

    request = ResourceDiscoveryRequest(
        query="machine learning",
    )

    import asyncio

    response = asyncio.run(
        discovery_service.discover(request)
    )

    assert response.query == "machine learning"

    assert response.total_results == 2

    assert len(response.resources) == 2


def test_discovery_searches_all_registered_providers(
    discovery_service,
    registry,
):

    import asyncio

    request = ResourceDiscoveryRequest(
        query="machine learning",
    )

    asyncio.run(
        discovery_service.discover(request)
    )

    registry.providers["openalex"].search.assert_awaited_once()

    registry.providers["youtube"].search.assert_awaited_once()


def test_discovery_supports_provider_selection(
    discovery_service,
    registry,
):

    import asyncio

    request = ResourceDiscoveryRequest(
        query="machine learning",
        providers=["openalex"],
    )

    response = asyncio.run(
        discovery_service.discover(request)
    )

    assert response.total_results == 1

    registry.providers["openalex"].search.assert_awaited_once()

    registry.providers["youtube"].search.assert_not_awaited()


def test_discovery_applies_resource_type_filter(
    discovery_service,
):

    import asyncio

    request = ResourceDiscoveryRequest(
        query="machine learning",
        resource_types=[
            ExternalResourceType.ARTICLE,
        ],
    )

    response = asyncio.run(
        discovery_service.discover(request)
    )

    assert response.total_results == 1

    assert (
        response.resources[0].resource_type
        == ExternalResourceType.ARTICLE
    )


def test_discovery_applies_language_filter(
    discovery_service,
):

    import asyncio

    request = ResourceDiscoveryRequest(
        query="machine learning",
        language="en",
    )

    response = asyncio.run(
        discovery_service.discover(request)
    )

    assert response.total_results == 2


def test_discovery_applies_subject_filter(
    discovery_service,
):

    import asyncio

    request = ResourceDiscoveryRequest(
        query="machine learning",
        subject="Computer Science",
    )

    response = asyncio.run(
        discovery_service.discover(request)
    )

    assert response.total_results == 2


def test_discovery_isolates_provider_failure(
    registry,
):

    registry.providers["youtube"].error = RuntimeError(
        "YouTube unavailable."
    )

    service = ResourceDiscoveryService(
        registry=registry,
    )

    import asyncio

    response = asyncio.run(
        service.discover(
            ResourceDiscoveryRequest(
                query="machine learning",
            )
        )
    )

    assert response.total_results == 1

    assert response.providers_searched == [
        "openalex",
    ]

    assert response.providers_failed == [
        "youtube",
    ]


def test_discovery_fails_when_all_providers_fail(
    registry,
):

    for provider in registry.providers.values():

        provider.error = RuntimeError(
            "Provider unavailable."
        )

    service = ResourceDiscoveryService(
        registry=registry,
    )

    import asyncio

    with pytest.raises(
        ResourceDiscoveryUnavailableError
    ):

        asyncio.run(
            service.discover(
                ResourceDiscoveryRequest(
                    query="machine learning",
                )
            )
        )


def test_discovery_rejects_unknown_provider(
    discovery_service,
):

    import asyncio

    request = ResourceDiscoveryRequest(
        query="machine learning",
        providers=["unknown_provider"],
    )

    with pytest.raises(
        ResourceDiscoveryValidationError
    ):

        asyncio.run(
            discovery_service.discover(request)
        )


def test_discovery_rejects_invalid_request(
    discovery_service,
):

    with pytest.raises(ValueError):

        ResourceDiscoveryRequest(
            query=" ",
        )


def test_discovery_rejects_invalid_limit():

    with pytest.raises(ValueError):

        ResourceDiscoveryRequest(
            query="machine learning",
            limit_per_provider=100,
        )


def test_discovery_rejects_invalid_concurrency(
    registry,
):

    with pytest.raises(ValueError):

        ResourceDiscoveryService(
            registry=registry,
            max_concurrent_providers=0,
        )


def test_discovery_returns_timezone_aware_timestamp(
    discovery_service,
):

    import asyncio

    response = asyncio.run(
        discovery_service.discover(
            ResourceDiscoveryRequest(
                query="machine learning",
            )
        )
    )

    assert response.retrieved_at.tzinfo is not None


def test_discovery_passes_requested_query_to_provider(
    discovery_service,
    registry,
):

    import asyncio

    request = ResourceDiscoveryRequest(
        query="neural networks",
    )

    asyncio.run(
        discovery_service.discover(request)
    )

    registry.providers["openalex"].search.assert_awaited_once_with(
        query="neural networks",
        limit=10,
    )


def test_discovery_preserves_provider_provenance(
    discovery_service,
):

    import asyncio

    response = asyncio.run(
        discovery_service.discover(
            ResourceDiscoveryRequest(
                query="machine learning",
            )
        )
    )

    providers = {
        resource.provider
        for resource in response.resources
    }

    assert providers == {
        "openalex",
        "youtube",
    }