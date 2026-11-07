import asyncio

import pytest

from unittest.mock import AsyncMock

from app.services.opportunities.discovery_service import (
    OpportunityDiscoveryService,
)

from app.services.opportunities.discovery_exceptions import (
    OpportunityDiscoveryUnavailableError,
)

from app.schemas.opportunities.discovery import (
    OpportunityDiscoveryRequest,
)


class FakeProvider:

    def __init__(self, results=None, error=None):

        self.results = results or []

        self.error = error

        self.search = AsyncMock(
            side_effect=self._search
        )

    async def _search(self, query, limit):

        if self.error is not None:
            raise self.error

        return self.results


class FakeRegistry:

    def __init__(self, providers):

        self.providers = providers

    def list_providers(self):

        return list(self.providers.keys())

    def get(self, name):

        return self.providers.get(name)


@pytest.mark.asyncio
async def test_provider_failure_isolation():

    successful_provider = FakeProvider(
        results=[]
    )

    failed_provider = FakeProvider(
        error=RuntimeError("Provider unavailable")
    )

    registry = FakeRegistry(
        {
            "provider_a": successful_provider,
            "provider_b": failed_provider,
        }
    )

    service = OpportunityDiscoveryService(
        registry=registry,
        max_concurrent_providers=2,
    )

    request = OpportunityDiscoveryRequest(
        query="Python internship",
        providers=None,
        opportunity_types=[],
        location=None,
        is_remote=None,
        limit_per_provider=10,
        max_results=20,
    )

    result = await service.discover(request)

    assert "provider_a" in result.providers_searched

    assert "provider_b" in result.providers_failed

    assert len(result.provider_failures) == 1


@pytest.mark.asyncio
async def test_all_provider_failures_raise_unavailable():

    registry = FakeRegistry(
        {
            "provider_a": FakeProvider(
                error=RuntimeError("Failure A")
            ),
            "provider_b": FakeProvider(
                error=RuntimeError("Failure B")
            ),
        }
    )

    service = OpportunityDiscoveryService(
        registry=registry,
    )

    request = OpportunityDiscoveryRequest(
        query="Python internship",
        providers=None,
        opportunity_types=[],
        location=None,
        is_remote=None,
        limit_per_provider=10,
        max_results=20,
    )

    with pytest.raises(
        OpportunityDiscoveryUnavailableError
    ):

        await service.discover(request)
        