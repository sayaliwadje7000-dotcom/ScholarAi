import pytest

from app.services.llm_providers.base import (
    BaseLLMProvider,
)

from app.services.llm_providers.exceptions import (
    LLMProviderConfigurationError,
)

from app.services.llm_providers.provider_registry import (
    LLMProviderRegistry,
)


class FakeProvider(BaseLLMProvider):

    name = "fake"

    async def generate(self, prompt):

        return "Fake response."


def test_registers_provider():

    registry = LLMProviderRegistry()

    provider = FakeProvider()

    registry.register(provider)

    assert registry.get("fake") is provider


def test_rejects_duplicate_provider():

    registry = LLMProviderRegistry()

    provider = FakeProvider()

    registry.register(provider)

    with pytest.raises(LLMProviderConfigurationError):

        registry.register(provider)


def test_rejects_unregistered_provider():

    registry = LLMProviderRegistry()

    with pytest.raises(LLMProviderConfigurationError):

        registry.get("unknown")


def test_lists_registered_providers():

    registry = LLMProviderRegistry()

    registry.register(
        FakeProvider()
    )

    assert registry.list_providers() == ["fake"]


def test_registry_clear():

    registry = LLMProviderRegistry()

    registry.register(
        FakeProvider()
    )

    registry.clear()

    assert registry.list_providers() == []