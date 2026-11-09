from app.services.llm_providers.gemini_provider import (
    GeminiProvider,
)

from app.services.llm_providers.provider_registry import (
    llm_provider_registry,
)


def register_default_llm_providers() -> None:

    if not llm_provider_registry.contains("gemini"):

        llm_provider_registry.register(
            GeminiProvider()
        )