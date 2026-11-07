import httpx
import pytest

from app.core.opportunity_provider_config import (
    OpportunityProviderSettings,
)

from app.integrations.opportunities.registry import (
    OpportunityProviderRegistry,
)

from app.integrations.opportunities.exceptions import (
    OpportunityProviderConfigurationError,
    OpportunityProviderDisabledError,
)


def test_disabled_registry_has_no_providers():

    settings = OpportunityProviderSettings(
        enabled=False,
    )

    registry = OpportunityProviderRegistry(
        settings=settings,
    )

    assert registry.list_providers() == []

    assert registry.settings.enabled is False


def test_enabled_registry_registers_adzuna():

    settings = OpportunityProviderSettings(
        enabled=True,
        adzuna_enabled=True,
        adzuna_app_id="test-id",
        adzuna_app_key="test-key",
    )

    registry = OpportunityProviderRegistry(
        settings=settings,
    )

    assert registry.list_providers() == [
        "adzuna"
    ]

    assert registry.get("adzuna").provider_name == "adzuna"


def test_registry_rejects_missing_credentials():

    settings = OpportunityProviderSettings(
        enabled=True,
        adzuna_enabled=True,
    )

    with pytest.raises(
        OpportunityProviderConfigurationError
    ):

        OpportunityProviderRegistry(
            settings=settings,
        )


def test_registry_rejects_unknown_provider():

    settings = OpportunityProviderSettings(
        enabled=True,
    )

    registry = OpportunityProviderRegistry(
        settings=settings,
    )

    with pytest.raises(
        OpportunityProviderConfigurationError
    ):

        registry.get("unknown")


def test_disabled_registry_rejects_provider_lookup():

    settings = OpportunityProviderSettings(
        enabled=False,
    )

    registry = OpportunityProviderRegistry(
        settings=settings,
    )

    with pytest.raises(
        OpportunityProviderDisabledError
    ):

        registry.get("adzuna")


@pytest.mark.asyncio
async def test_registry_closes_owned_client():

    settings = OpportunityProviderSettings()

    registry = OpportunityProviderRegistry(
        settings=settings,
    )

    client = registry.client

    await registry.close()

    assert client.is_closed


@pytest.mark.asyncio
async def test_registry_does_not_close_injected_client():

    settings = OpportunityProviderSettings()

    client = httpx.AsyncClient()

    registry = OpportunityProviderRegistry(
        settings=settings,
        client=client,
    )

    await registry.close()

    assert client.is_closed is False

    await client.aclose()