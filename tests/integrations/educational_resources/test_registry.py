import httpx
import pytest

from app.core.resource_provider_config import (
    ResourceProviderSettings,
)

from app.integrations.educational_resources.registry import (
    ResourceProviderRegistry,
)

from app.integrations.educational_resources.exceptions import (
    ResourceProviderConfigurationError,
    ResourceProviderDisabledError,
)


def test_registry_registers_available_providers():

    settings = ResourceProviderSettings(
        youtube_api_key="test-key",
    )

    registry = ResourceProviderRegistry(
        settings=settings,
    )

    assert registry.list_providers() == [
        "crossref",
        "google_books",
        "openalex",
        "youtube",
    ]

    import asyncio
    asyncio.run(registry.close())


def test_registry_skips_youtube_without_key():

    settings = ResourceProviderSettings()

    registry = ResourceProviderRegistry(
        settings=settings,
    )

    assert "youtube" not in registry.list_providers()

    assert "openalex" in registry.list_providers()

    import asyncio
    asyncio.run(registry.close())


def test_registry_get_unknown_provider():

    registry = ResourceProviderRegistry(
        settings=ResourceProviderSettings()
    )

    with pytest.raises(
        ResourceProviderConfigurationError
    ):

        registry.get("unknown")

    import asyncio
    asyncio.run(registry.close())


def test_registry_disabled():

    registry = ResourceProviderRegistry(
        settings=ResourceProviderSettings(
            enabled=False,
        )
    )

    assert registry.list_providers() == []

    with pytest.raises(
        ResourceProviderDisabledError
    ):

        registry.get("openalex")

    import asyncio
    asyncio.run(registry.close())


@pytest.mark.asyncio
async def test_registry_does_not_close_injected_client():

    client = httpx.AsyncClient()

    registry = ResourceProviderRegistry(
        settings=ResourceProviderSettings(),
        client=client,
    )

    await registry.close()

    assert not client.is_closed

    await client.aclose()