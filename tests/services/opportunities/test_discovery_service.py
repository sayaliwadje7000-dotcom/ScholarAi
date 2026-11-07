import asyncio

from datetime import datetime, timezone

import pytest

from app.schemas.opportunities.discovery import (
    OpportunityDiscoveryRequest,
)

from app.schemas.opportunities.opportunity import (
    OpportunityCreate,
)

from app.services.opportunities.discovery_service import (
    OpportunityDiscoveryService,
)

from app.services.opportunities.discovery_exceptions import (
    OpportunityDiscoveryUnavailableError,
    OpportunityDiscoveryValidationError,
)


# ---------------------------------------------------------
# TEST PROVIDER
# ---------------------------------------------------------

class FakeOpportunityProvider:

    def __init__(
        self,
        name: str,
        results=None,
        error=None,
        delay: float = 0,
    ):

        self.name = name

        self.results = results or []

        self.error = error

        self.delay = delay

        self.calls = 0

    async def search(
        self,
        query: str,
        limit: int,
    ):

        self.calls += 1

        if self.delay:
            await asyncio.sleep(self.delay)

        if self.error:
            raise self.error

        return self.results[:limit]


class FakeRegistry:

    def __init__(self, providers):

        self.providers = providers

    def list_providers(self):

        return sorted(self.providers.keys())

    def get(self, provider_name):

        return self.providers.get(provider_name)


# ---------------------------------------------------------
# TEST DATA
# ---------------------------------------------------------

def make_opportunity(
    provider="adzuna",
    title="Python Internship",
    opportunity_type="internship",
    location="Pune",
    is_remote=False,
):

    return OpportunityCreate(
        provider=provider,
        external_id=f"{provider}-123",
        title=title,
        description="Python development opportunity.",
        opportunity_type=opportunity_type,
        official_url="https://example.com/opportunity",
        source_url="https://example.com/source",
        application_url="https://example.com/apply",
        eligibility="Undergraduate students",
        required_skills=["Python"],
        location=location,
        is_remote=is_remote,
        status="open",
        verification_status="unverified",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "source": provider,
        },
    )


def make_request(**overrides):

    data = {
        "query": "Python internship",
        "limit_per_provider": 10,
        "max_results": 50,
    }

    data.update(overrides)

    return OpportunityDiscoveryRequest(**data)


# ---------------------------------------------------------
# INITIALIZATION TESTS
# ---------------------------------------------------------

def test_service_initialization():

    registry = FakeRegistry({})

    service = OpportunityDiscoveryService(
        registry=registry,
    )

    assert service.registry is registry

    assert service.max_concurrent_providers == 4


def test_service_rejects_missing_registry():

    with pytest.raises(TypeError):

        OpportunityDiscoveryService(
            registry=None,
        )


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        1.5,
        True,
        "4",
    ],
)
def test_service_rejects_invalid_concurrency(value):

    with pytest.raises(ValueError):

        OpportunityDiscoveryService(
            registry=FakeRegistry({}),
            max_concurrent_providers=value,
        )


# ---------------------------------------------------------
# PROVIDER SELECTION TESTS
# ---------------------------------------------------------

def test_available_provider_names():

    registry = FakeRegistry(
        {
            "adzuna": FakeOpportunityProvider("adzuna"),
        }
    )

    service = OpportunityDiscoveryService(registry)

    assert service._available_provider_names() == [
        "adzuna",
    ]


def test_unknown_provider_is_rejected():

    registry = FakeRegistry(
        {
            "adzuna": FakeOpportunityProvider("adzuna"),
        }
    )

    service = OpportunityDiscoveryService(registry)

    request = make_request(
        providers=["unknown_provider"],
    )

    with pytest.raises(
        OpportunityDiscoveryValidationError,
    ):

        service._select_providers(
            request.providers,
        )


# ---------------------------------------------------------
# PROVIDER RESPONSE VALIDATION TESTS
# ---------------------------------------------------------

def test_provider_results_are_validated():

    opportunity = make_opportunity()

    results = (
        OpportunityDiscoveryService
        ._validate_provider_results(
            "adzuna",
            [opportunity],
        )
    )

    assert len(results) == 1

    assert results[0].title == "Python Internship"


def test_provider_results_must_be_a_list():

    with pytest.raises(Exception):

        OpportunityDiscoveryService._validate_provider_results(
            "adzuna",
            "invalid",
        )


def test_provider_provenance_must_match():

    opportunity = make_opportunity(
        provider="different_provider",
    )

    with pytest.raises(Exception):

        OpportunityDiscoveryService._validate_provider_results(
            "adzuna",
            [opportunity],
        )


# ---------------------------------------------------------
# FILTERING TESTS
# ---------------------------------------------------------

def test_category_filter():

    opportunity = make_opportunity(
        opportunity_type="internship",
    )

    request = make_request(
        opportunity_types=["hackathon"],
    )

    assert (
        OpportunityDiscoveryService._matches_filters(
            opportunity,
            request,
        )
        is False
    )


def test_location_filter():

    opportunity = make_opportunity(
        location="Pune",
    )

    matching_request = make_request(
        location="Pune",
    )

    nonmatching_request = make_request(
        location="Mumbai",
    )

    assert (
        OpportunityDiscoveryService._matches_filters(
            opportunity,
            matching_request,
        )
        is True
    )

    assert (
        OpportunityDiscoveryService._matches_filters(
            opportunity,
            nonmatching_request,
        )
        is False
    )


def test_remote_filter():

    opportunity = make_opportunity(
        is_remote=True,
    )

    request = make_request(
        is_remote=True,
    )

    assert (
        OpportunityDiscoveryService._matches_filters(
            opportunity,
            request,
        )
        is True
    )


# ---------------------------------------------------------
# DISCOVERY TESTS
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_discover_from_single_provider():

    opportunity = make_opportunity()

    provider = FakeOpportunityProvider(
        name="adzuna",
        results=[opportunity],
    )

    registry = FakeRegistry(
        {
            "adzuna": provider,
        }
    )

    service = OpportunityDiscoveryService(registry)

    response = await service.discover(
        make_request(),
    )

    assert response.total_results == 1

    assert len(response.opportunities) == 1

    assert response.providers_searched == [
        "adzuna",
    ]

    assert response.providers_failed == []


@pytest.mark.asyncio
async def test_discover_from_multiple_providers():

    adzuna_opportunity = make_opportunity(
        provider="adzuna",
        title="Python Internship",
    )

    provider_two_opportunity = make_opportunity(
        provider="provider_two",
        title="Backend Internship",
    )

    registry = FakeRegistry(
        {
            "adzuna": FakeOpportunityProvider(
                "adzuna",
                [adzuna_opportunity],
            ),
            "provider_two": FakeOpportunityProvider(
                "provider_two",
                [provider_two_opportunity],
            ),
        }
    )

    service = OpportunityDiscoveryService(registry)

    response = await service.discover(
        make_request(),
    )

    assert response.total_results == 2

    assert len(response.providers_searched) == 2


@pytest.mark.asyncio
async def test_provider_failure_does_not_cancel_other_providers():

    working_opportunity = make_opportunity()

    registry = FakeRegistry(
        {
            "adzuna": FakeOpportunityProvider(
                "adzuna",
                results=[working_opportunity],
            ),
            "failing": FakeOpportunityProvider(
                "failing",
                error=RuntimeError("External API failed"),
            ),
        }
    )

    service = OpportunityDiscoveryService(registry)

    response = await service.discover(
        make_request(),
    )

    assert response.total_results == 1

    assert "adzuna" in response.providers_searched

    assert "failing" in response.providers_failed

    assert len(response.provider_failures) == 1


@pytest.mark.asyncio
async def test_all_provider_failures_raise_unavailable():

    registry = FakeRegistry(
        {
            "adzuna": FakeOpportunityProvider(
                "adzuna",
                error=RuntimeError("Failure"),
            ),
        }
    )

    service = OpportunityDiscoveryService(registry)

    with pytest.raises(
        OpportunityDiscoveryUnavailableError,
    ):

        await service.discover(
            make_request(),
        )


@pytest.mark.asyncio
async def test_empty_provider_results_are_successful():

    registry = FakeRegistry(
        {
            "adzuna": FakeOpportunityProvider(
                "adzuna",
                results=[],
            ),
        }
    )

    service = OpportunityDiscoveryService(registry)

    response = await service.discover(
        make_request(),
    )

    assert response.total_results == 0

    assert response.providers_searched == [
        "adzuna",
    ]


@pytest.mark.asyncio
async def test_overall_result_limit_is_enforced():

    opportunities = [
        make_opportunity(
            title=f"Internship {index}",
        )
        for index in range(5)
    ]

    registry = FakeRegistry(
        {
            "adzuna": FakeOpportunityProvider(
                "adzuna",
                opportunities,
            ),
        }
    )

    service = OpportunityDiscoveryService(registry)

    response = await service.discover(
        make_request(
            max_results=2,
        ),
    )

    assert response.total_results == 2

    assert len(response.opportunities) == 2


@pytest.mark.asyncio
async def test_discovery_rejects_invalid_request_type():

    service = OpportunityDiscoveryService(
        FakeRegistry(
            {
                "adzuna": FakeOpportunityProvider("adzuna"),
            }
        )
    )

    with pytest.raises(TypeError):

        await service.discover(
            {"query": "Python"},
        )


@pytest.mark.asyncio
async def test_discovery_uses_requested_providers_only():

    adzuna = FakeOpportunityProvider("adzuna")

    provider_two = FakeOpportunityProvider("provider_two")

    registry = FakeRegistry(
        {
            "adzuna": adzuna,
            "provider_two": provider_two,
        }
    )

    service = OpportunityDiscoveryService(registry)

    await service.discover(
        make_request(
            providers=["adzuna"],
        ),
    )

    assert adzuna.calls == 1

    assert provider_two.calls == 0


@pytest.mark.asyncio
async def test_provider_results_are_filtered_by_category():

    internship = make_opportunity(
        title="Python Internship",
        opportunity_type="internship",
    )

    registry = FakeRegistry(
        {
            "adzuna": FakeOpportunityProvider(
                "adzuna",
                [internship],
            ),
        }
    )

    service = OpportunityDiscoveryService(registry)

    response = await service.discover(
        make_request(
            opportunity_types=["hackathon"],
        ),
    )

    assert response.total_results == 0