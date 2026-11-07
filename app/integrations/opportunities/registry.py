import httpx

from app.core.opportunity_provider_config import (
    OpportunityProviderSettings,
    get_opportunity_provider_settings,
)

from app.integrations.opportunities.exceptions import (
    OpportunityProviderConfigurationError,
    OpportunityProviderDisabledError,
)

from app.integrations.opportunities.providers import (
    AdzunaProvider,
)


class OpportunityProviderRegistry:

    def __init__(
        self,
        settings: OpportunityProviderSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ):

        self.settings = (
            settings or get_opportunity_provider_settings()
        )

        self._owns_client = client is None

        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                self.settings.timeout_seconds
            ),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
            ),
            headers={
                "User-Agent": "ScholarAI/0.1.0",
                "Accept": "application/json",
            },
        )

        self._providers = {}

        if self.settings.enabled:
            self._register_available_providers()

    def _register_available_providers(self):

        provider_definitions = {
            "adzuna": (
                AdzunaProvider,
                self.settings.adzuna_enabled,
                self.settings.adzuna_configured,
            ),
        }

        for name, (
            provider_class,
            enabled,
            configured,
        ) in provider_definitions.items():

            if not enabled:
                continue

            if not configured:

                raise OpportunityProviderConfigurationError(
                    f"Provider '{name}' is enabled, but credentials are missing."
                )

            self._providers[name] = provider_class(
                client=self.client,
                settings=self.settings,
            )

    def get(self, provider_name: str):

        if not self.settings.enabled:

            raise OpportunityProviderDisabledError(
                "Opportunity discovery is disabled."
            )

        provider = self._providers.get(provider_name)

        if provider is None:

            raise OpportunityProviderConfigurationError(
                f"Provider '{provider_name}' is not registered or enabled."
            )

        return provider

    def list_providers(self) -> list[str]:

        return sorted(self._providers.keys())

    async def health_check(self) -> dict:

        if not self.settings.enabled:

            return {
                "status": "disabled",
                "providers": {},
            }

        provider_status = {}

        for name, provider in self._providers.items():

            try:
                provider_status[name] = await provider.health_check()

            except Exception:
                provider_status[name] = {
                    "provider": name,
                    "status": "unhealthy",
                }

        return {
            "status": "enabled",
            "providers": provider_status,
        }

    async def close(self):

        if self._owns_client:
            await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):

        await self.close()