import httpx
import pytest

from app.core.resource_provider_config import (
    ResourceProviderSettings,
)

from app.integrations.educational_resources.base import (
    BaseResourceProvider,
)

from app.integrations.educational_resources.exceptions import (
    ResourceProviderAuthenticationError,
    ResourceProviderRateLimitError,
    ResourceProviderResponseError,
)


class DummyProvider(BaseResourceProvider):

    provider_name = "dummy"

    async def search(
        self,
        query,
        limit=10,
        **filters,
    ):
        return []

    def normalize(self, payload):
        return None


@pytest.mark.asyncio
async def test_request_json_success():

    async def handler(request):

        return httpx.Response(
            200,
            json={"results": []},
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    settings = ResourceProviderSettings(
        max_retries=0,
    )

    provider = DummyProvider(
        client,
        settings,
    )

    result = await provider._request_json(
        "GET",
        "https://example.com",
    )

    assert result == {"results": []}

    await client.aclose()


@pytest.mark.asyncio
async def test_request_json_authentication_error():

    async def handler(request):

        return httpx.Response(
            401,
            json={"error": "unauthorized"},
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = DummyProvider(
        client,
        ResourceProviderSettings(
            max_retries=0,
        ),
    )

    with pytest.raises(
        ResourceProviderAuthenticationError
    ):

        await provider._request_json(
            "GET",
            "https://example.com",
        )

    await client.aclose()


@pytest.mark.asyncio
async def test_request_json_rate_limit_error():

    async def handler(request):

        return httpx.Response(
            429,
            json={"error": "rate limited"},
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = DummyProvider(
        client,
        ResourceProviderSettings(
            max_retries=0,
        ),
    )

    with pytest.raises(
        ResourceProviderRateLimitError
    ):

        await provider._request_json(
            "GET",
            "https://example.com",
        )

    await client.aclose()


@pytest.mark.asyncio
async def test_request_json_invalid_json():

    async def handler(request):

        return httpx.Response(
            200,
            content=b"invalid json",
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = DummyProvider(
        client,
        ResourceProviderSettings(
            max_retries=0,
        ),
    )

    with pytest.raises(
        ResourceProviderResponseError
    ):

        await provider._request_json(
            "GET",
            "https://example.com",
        )

    await client.aclose()