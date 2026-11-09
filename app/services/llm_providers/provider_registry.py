from app.services.llm_providers.base import (
    BaseLLMProvider,
)

from app.services.llm_providers.exceptions import (
    LLMProviderConfigurationError,
)


class LLMProviderRegistry:

    def __init__(self):

        self._providers: dict[
            str,
            BaseLLMProvider,
        ] = {}

    def register(
        self,
        provider: BaseLLMProvider,
    ) -> None:

        name = getattr(
            provider,
            "name",
            None,
        )

        if not isinstance(name, str) or not name.strip():

            raise LLMProviderConfigurationError(
                "Provider must have a valid name."
            )

        name = name.strip().lower()

        if name in self._providers:

            raise LLMProviderConfigurationError(
                f"Provider '{name}' is already registered."
            )

        if not isinstance(
            provider,
            BaseLLMProvider,
        ):

            raise LLMProviderConfigurationError(
                "Provider must implement BaseLLMProvider."
            )

        self._providers[name] = provider

    def get(
        self,
        name: str,
    ) -> BaseLLMProvider:

        provider = self._providers.get(
            name.strip().lower()
        )

        if provider is None:

            raise LLMProviderConfigurationError(
                f"LLM provider '{name}' is not registered."
            )

        return provider

    def contains(
        self,
        name: str,
    ) -> bool:

        return name.strip().lower() in self._providers

    def list_providers(self) -> list[str]:

        return list(
            self._providers.keys()
        )

    def clear(self) -> None:

        self._providers.clear()


llm_provider_registry = LLMProviderRegistry()