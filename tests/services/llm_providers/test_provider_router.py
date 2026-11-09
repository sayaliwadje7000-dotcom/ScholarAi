import pytest

from app.core.llm_provider_config import (
    LLMProviderSettings,
)

from app.services.llm_providers.base import (
    BaseLLMProvider,
)

from app.services.llm_providers.exceptions import (
    LLMProviderUnavailableError,
    LLMAllProvidersFailedError,
)

from app.services.llm_providers.provider_registry import (
    LLMProviderRegistry,
)

from app.services.llm_providers.provider_router import (
    LLMProviderRouter,
)

from app.schemas.llm_provider import (
    LLMProviderStatus,
)


class SuccessfulProvider(BaseLLMProvider):

    name = "primary"

    async def generate(self, prompt):

        return "Primary response."


class FailingProvider(BaseLLMProvider):

    name = "primary"

    async def generate(self, prompt):

        raise LLMProviderUnavailableError(
            "Primary unavailable."
        )


class FallbackProvider(BaseLLMProvider):

    name = "fallback"

    async def generate(self, prompt):

        return "Fallback response."


class PermanentlyFailingProvider(BaseLLMProvider):

    name = "primary"

    async def generate(self, prompt):

        raise RuntimeError(
            "Permanent failure."
        )


@pytest.fixture
def registry():

    registry = LLMProviderRegistry()

    return registry


@pytest.mark.asyncio
async def test_primary_provider_success(registry):

    registry.register(
        SuccessfulProvider()
    )

    router = LLMProviderRouter(
        registry=registry,
        settings=LLMProviderSettings(
            primary_provider="primary",
            fallback_providers=(),
        ),
    )

    result = await router.generate(
        "Explain binary search."
    )

    assert result.response == "Primary response."

    assert result.provider == "primary"

    assert result.status == LLMProviderStatus.SUCCESS

    assert len(result.attempts) == 1


@pytest.mark.asyncio
async def test_fallback_provider_success(registry):

    registry.register(
        FailingProvider()
    )

    registry.register(
        FallbackProvider()
    )

    router = LLMProviderRouter(
        registry=registry,
        settings=LLMProviderSettings(
            primary_provider="primary",
            fallback_providers=("fallback",),
        ),
    )

    result = await router.generate(
        "Explain binary search."
    )

    assert result.response == "Fallback response."

    assert result.provider == "fallback"

    assert result.status == (
        LLMProviderStatus.FALLBACK_SUCCESS
    )

    assert len(result.attempts) == 2

    assert result.attempts[0].retryable is True


@pytest.mark.asyncio
async def test_all_providers_unavailable(registry):

    registry.register(
        FailingProvider()
    )

    class SecondFailingProvider(BaseLLMProvider):

        name = "fallback"

        async def generate(self, prompt):

            raise LLMProviderUnavailableError(
                "Fallback unavailable."
            )

    registry.register(
        SecondFailingProvider()
    )

    router = LLMProviderRouter(
        registry=registry,
        settings=LLMProviderSettings(
            primary_provider="primary",
            fallback_providers=("fallback",),
        ),
    )

    with pytest.raises(LLMAllProvidersFailedError) as exc:

        await router.generate(
            "Explain binary search."
        )

    assert len(exc.value.attempts) == 2


@pytest.mark.asyncio
async def test_stops_after_non_retryable_failure(registry):

    registry.register(
        PermanentlyFailingProvider()
    )

    registry.register(
        FallbackProvider()
    )

    router = LLMProviderRouter(
        registry=registry,
        settings=LLMProviderSettings(
            primary_provider="primary",
            fallback_providers=("fallback",),
        ),
    )

    with pytest.raises(LLMAllProvidersFailedError) as exc:

        await router.generate(
            "Explain binary search."
        )

    assert len(exc.value.attempts) == 1


@pytest.mark.asyncio
async def test_rejects_empty_prompt(registry):

    router = LLMProviderRouter(
        registry=registry,
        settings=LLMProviderSettings(
            primary_provider="primary",
            fallback_providers=(),
        ),
    )

    with pytest.raises(ValueError):

        await router.generate("   ")


@pytest.mark.asyncio
async def test_rejects_unregistered_fallback(registry):

    registry.register(
        SuccessfulProvider()
    )

    router = LLMProviderRouter(
        registry=registry,
        settings=LLMProviderSettings(
            primary_provider="primary",
            fallback_providers=("missing",),
        ),
    )

    from app.services.llm_providers.exceptions import (
        LLMProviderConfigurationError,
    )

    with pytest.raises(LLMProviderConfigurationError):

        await router.generate(
            "Explain binary search."
        )