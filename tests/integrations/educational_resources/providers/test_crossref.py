import httpx
import pytest

from app.core.resource_provider_config import (
    ResourceProviderSettings,
)

from app.integrations.educational_resources.providers.crossref import (
    CrossrefProvider,
)

from app.schemas.external_resources import (
    ExternalResourceType,
)


def test_crossref_normalization():

    provider = CrossrefProvider(
        httpx.AsyncClient(),
        ResourceProviderSettings(),
    )

    resource = provider.normalize({
        "DOI": "10.1234/example",
        "title": [
            "Deep Learning Research"
        ],
        "author": [
            {
                "given": "John",
                "family": "Doe",
            }
        ],
        "publisher": "Example Publisher",
        "published": {
            "date-parts": [
                [2025, 5, 12]
            ]
        },
    })

    assert resource is not None

    assert resource.external_id == "10.1234/example"

    assert resource.resource_type == (
        ExternalResourceType.ARTICLE
    )

    assert resource.authors == ("John Doe",)

    assert resource.canonical_url == (
        "https://doi.org/10.1234/example"
    )


@pytest.mark.asyncio
async def test_crossref_search():

    def handler(request):

        assert request.url.params["query"] == "Python"

        return httpx.Response(
            200,
            json={
                "message": {
                    "items": [
                        {
                            "DOI": "10.1234/example",
                            "title": ["Python Research"],
                        }
                    ]
                }
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    provider = CrossrefProvider(
        client,
        ResourceProviderSettings(
            max_retries=0,
        ),
    )

    results = await provider.search("Python")

    assert len(results) == 1

    assert results[0].title == "Python Research"

    await client.aclose()