import httpx
import pytest

from app.core.opportunity_provider_config import (
    OpportunityProviderSettings,
)

from app.integrations.opportunities.providers.adzuna import (
    AdzunaProvider,
)

from app.integrations.opportunities.exceptions import (
    OpportunityProviderAuthenticationError,
    OpportunityProviderResponseError,
)


@pytest.fixture
def settings():

    return OpportunityProviderSettings(
        enabled=True,
        adzuna_enabled=True,
        adzuna_app_id="test-id",
        adzuna_app_key="test-key",
        adzuna_country="gb",
        max_retries=0,
    )


@pytest.mark.asyncio
async def test_adzuna_search_returns_results(settings):

    def handler(request):

        assert request.url.path == (
            "/v1/api/jobs/gb/search/1"
        )

        assert request.url.params["what"] == "python internship"

        assert request.url.params["app_id"] == "test-id"

        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "123",
                        "title": "Python Intern",
                        "description": "Python development internship",
                        "redirect_url": "https://example.com/job/123",
                    }
                ]
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = AdzunaProvider(
        client=client,
        settings=settings,
    )

    results = await provider.search(
        "python internship",
        limit=5,
    )

    assert len(results) == 1

    assert results[0]["id"] == "123"

    assert results[0]["title"] == "Python Intern"

    await client.aclose()


@pytest.mark.asyncio
async def test_adzuna_search_supports_location(settings):

    def handler(request):

        assert request.url.params["where"] == "London"

        return httpx.Response(
            200,
            json={
                "results": []
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = AdzunaProvider(
        client=client,
        settings=settings,
    )

    results = await provider.search(
        "software internship",
        location="London",
    )

    assert results == []

    await client.aclose()


@pytest.mark.asyncio
async def test_adzuna_search_rejects_empty_query(settings):

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={})
        )
    )

    provider = AdzunaProvider(
        client=client,
        settings=settings,
    )

    results = await provider.search("   ")

    assert results == []

    await client.aclose()


@pytest.mark.asyncio
async def test_adzuna_authentication_error(settings):

    def handler(request):

        return httpx.Response(401)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = AdzunaProvider(
        client=client,
        settings=settings,
    )

    with pytest.raises(
        OpportunityProviderAuthenticationError
    ):

        await provider.search("python internship")

    await client.aclose()


@pytest.mark.asyncio
async def test_adzuna_invalid_response_is_rejected(settings):

    def handler(request):

        return httpx.Response(
            200,
            json={
                "results": "invalid"
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = AdzunaProvider(
        client=client,
        settings=settings,
    )

    with pytest.raises(
        OpportunityProviderResponseError
    ):

        await provider.search("python internship")

    await client.aclose()


@pytest.mark.asyncio
async def test_adzuna_invalid_page_is_rejected(settings):

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={})
        )
    )

    provider = AdzunaProvider(
        client=client,
        settings=settings,
    )

    with pytest.raises(
        OpportunityProviderResponseError
    ):

        await provider.search(
            "python internship",
            page=0,
        )

    await client.aclose()