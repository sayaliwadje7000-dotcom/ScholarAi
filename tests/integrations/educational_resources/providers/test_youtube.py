import httpx
import pytest

from app.core.resource_provider_config import (
    ResourceProviderSettings,
)

from app.integrations.educational_resources.providers.youtube import (
    YouTubeProvider,
)

from app.integrations.educational_resources.exceptions import (
    ResourceProviderConfigurationError,
    ResourceProviderValidationError,
)

from app.schemas.external_resources import (
    ExternalResourceType,
)


def test_youtube_requires_api_key():

    with pytest.raises(
        ResourceProviderConfigurationError
    ):

        YouTubeProvider(
            httpx.AsyncClient(),
            ResourceProviderSettings(),
        )


def test_youtube_normalization():

    provider = YouTubeProvider(
        httpx.AsyncClient(),
        ResourceProviderSettings(
            youtube_api_key="test-key",
        ),
    )

    resource = provider.normalize({
        "id": {
            "videoId": "abc123",
        },
        "snippet": {
            "title": "Python Tutorial",
            "description": "Learn Python",
            "channelTitle": "ScholarAI",
            "channelId": "channel123",
            "publishedAt": "2025-01-01T00:00:00Z",
            "thumbnails": {},
        },
    })

    assert resource is not None

    assert resource.provider == "youtube"

    assert resource.external_id == "abc123"

    assert resource.resource_type == (
        ExternalResourceType.VIDEO
    )

    assert resource.canonical_url.endswith(
        "v=abc123"
    )


@pytest.mark.asyncio
async def test_youtube_search():

    def handler(request):

        assert request.url.params["q"] == "Python"

        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": {
                            "videoId": "abc123",
                        },
                        "snippet": {
                            "title": "Python Tutorial",
                            "description": "Learn Python",
                            "channelTitle": "ScholarAI",
                            "publishedAt": "2025-01-01T00:00:00Z",
                        },
                    }
                ]
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = YouTubeProvider(
        client,
        ResourceProviderSettings(
            youtube_api_key="test-key",
            max_retries=0,
        ),
    )

    results = await provider.search(
        "Python",
        limit=5,
    )

    assert len(results) == 1

    assert results[0].title == "Python Tutorial"

    await client.aclose()


@pytest.mark.asyncio
async def test_youtube_rejects_empty_query():

    provider = YouTubeProvider(
        httpx.AsyncClient(),
        ResourceProviderSettings(
            youtube_api_key="test-key",
        ),
    )

    with pytest.raises(
        ResourceProviderValidationError
    ):

        await provider.search("   ")

    await provider.client.aclose()