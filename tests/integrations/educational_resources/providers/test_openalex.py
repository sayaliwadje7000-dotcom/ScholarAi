import httpx
import pytest

from app.core.resource_provider_config import (
    ResourceProviderSettings,
)

from app.integrations.educational_resources.providers.openalex import (
    OpenAlexProvider,
)

from app.schemas.external_resources import (
    ExternalResourceType,
    ExternalAccessType,
)


def test_openalex_normalization():

    provider = OpenAlexProvider(
        httpx.AsyncClient(),
        ResourceProviderSettings(),
    )

    resource = provider.normalize({
        "id": "https://openalex.org/W123",
        "doi": "https://doi.org/10.1234/example",
        "title": "Machine Learning",
        "publication_date": "2025-01-01",
        "publication_year": 2025,
        "authorships": [
            {
                "author": {
                    "display_name": "John Doe",
                }
            }
        ],
        "open_access": {
            "is_oa": True,
        },
        "best_oa_location": {
            "license": "cc-by",
        },
    })

    assert resource is not None

    assert resource.provider == "openalex"

    assert resource.resource_type == (
        ExternalResourceType.ARTICLE
    )

    assert resource.access_type == (
        ExternalAccessType.OPEN_ACCESS
    )

    assert resource.authors == ("John Doe",)


@pytest.mark.asyncio
async def test_openalex_search():

    def handler(request):

        assert request.url.params["search"] == "AI"

        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "title": "Artificial Intelligence",
                        "authorships": [],
                    }
                ]
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = OpenAlexProvider(
        client,
        ResourceProviderSettings(
            max_retries=0,
        ),
    )

    results = await provider.search("AI")

    assert len(results) == 1

    assert results[0].title == (
        "Artificial Intelligence"
    )

    await client.aclose()