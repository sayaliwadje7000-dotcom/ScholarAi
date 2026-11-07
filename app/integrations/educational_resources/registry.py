import httpx

from app.core.resource_provider_config import (
    ResourceProviderSettings,
    get_resource_provider_settings,
)

from app.integrations.educational_resources.exceptions import (
    ResourceProviderConfigurationError,
    ResourceProviderDisabledError,
)

from app.integrations.educational_resources.providers import (
    YouTubeProvider,
    OpenAlexProvider,
    CrossrefProvider,
    GoogleBooksProvider,
)


class ResourceProviderRegistry:

    def __init__(
        self,
        settings: ResourceProviderSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ):

        self.settings = (
            settings or get_resource_provider_settings()
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

        if not self.settings.enabled:
            return

        self._register_available_providers()

    def _register_available_providers(self):

        provider_definitions = {
            "youtube": (
                YouTubeProvider,
                self.settings.youtube_api_key,
            ),

            "openalex": (
                OpenAlexProvider,
                True,
            ),

            "crossref": (
                CrossrefProvider,
                True,
            ),

            "google_books": (
                GoogleBooksProvider,
                True,
            ),
        }

        for name, (
            provider_class,
            availability,
        ) in provider_definitions.items():

            if not availability:
                continue

            try:

                self._providers[name] = provider_class(
                    client=self.client,
                    settings=self.settings,
                )

            except ResourceProviderConfigurationError:
                continue

    def get(self, provider_name: str):

        if not self.settings.enabled:

            raise ResourceProviderDisabledError(
                "External resource discovery is disabled."
            )

        provider = self._providers.get(
            provider_name
        )

        if provider is None:

            raise ResourceProviderConfigurationError(
                f"Provider '{provider_name}' is "
                "not configured or not registered."
            )

        return provider

    def list_providers(self) -> list[str]:

        return sorted(
            self._providers.keys()
        )

    async def health_check(self) -> dict:

        return {
            name: await provider.health_check()
            for name, provider in self._providers.items()
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