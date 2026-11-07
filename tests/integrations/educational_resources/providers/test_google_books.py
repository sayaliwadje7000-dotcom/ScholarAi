import httpx
import pytest

from app.core.resource_provider_config import (
    ResourceProviderSettings,
)

from app.integrations.educational_resources.providers.google_books import (
    GoogleBooksProvider,
)

from app.schemas.external_resources import (
    ExternalAccessType,
    ExternalResourceType,
)


def test_google_books_normalization():

    provider = GoogleBooksProvider(
        httpx.AsyncClient(),
        ResourceProviderSettings(),
    )

    resource = provider.normalize({
        "id": "book123",
        "volumeInfo": {
            "title": "Python Programming",
            "authors": ["John Doe"],
            "publishedDate": "2025-01",
            "description": "Learn Python",
            "language": "en",
            "publisher": "Example Publisher",
            "pageCount": 300,
            "industryIdentifiers": [],
        },
        "accessInfo": {
            "accessViewStatus": "SAMPLE",
        },
    })

    assert resource is not None

    assert resource.provider == "google_books"

    assert resource.external_id == "book123"

    assert resource.resource_type == (
        ExternalResourceType.BOOK
    )

    assert resource.access_type == (
        ExternalAccessType.PREVIEW
    )

    assert resource.authors == ("John Doe",)


@pytest.mark.asyncio
async def test_google_books_search():

    def handler(request):

        assert request.url.params["q"] == "Python"

        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "book123",
                        "volumeInfo": {
                            "title": "Python Programming",
                            "authors": ["John Doe"],
                        },
                    }
                ]
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = GoogleBooksProvider(
        client,
        ResourceProviderSettings(
            max_retries=0,
        ),
    )

    results = await provider.search("Python")

    assert len(results) == 1

    assert results[0].title == "Python Programming"

    await client.aclose()