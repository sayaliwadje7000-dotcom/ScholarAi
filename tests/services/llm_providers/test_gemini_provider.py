import pytest

from app.services.llm_providers.exceptions import (
    LLMProviderAuthenticationError,
    LLMProviderConfigurationError,
    LLMProviderExecutionError,
    LLMProviderUnavailableError,
)

from app.services.llm_providers.gemini_provider import (
    GeminiProvider,
)


@pytest.mark.asyncio
async def test_gemini_provider_success():

    async def fake_generator(prompt):

        assert prompt == "Explain binary search."

        return "Binary search is a searching algorithm."

    provider = GeminiProvider(
        generator=fake_generator
    )

    result = await provider.generate(
        " Explain binary search. "
    )

    assert result == (
        "Binary search is a searching algorithm."
    )


@pytest.mark.asyncio
async def test_rejects_empty_prompt():

    provider = GeminiProvider(
        generator=None
    )

    with pytest.raises(ValueError):

        await provider.generate("   ")


@pytest.mark.asyncio
async def test_maps_temporary_failure():

    async def fake_generator(prompt):

        raise RuntimeError(
            "Gemini is temporarily unavailable."
        )

    provider = GeminiProvider(
        generator=fake_generator
    )

    with pytest.raises(LLMProviderUnavailableError):

        await provider.generate("Explain operating systems.")


@pytest.mark.asyncio
async def test_maps_quota_failure():

    async def fake_generator(prompt):

        raise RuntimeError(
            "Gemini API usage limit reached."
        )

    provider = GeminiProvider(
        generator=fake_generator
    )

    with pytest.raises(LLMProviderUnavailableError):

        await provider.generate("Explain databases.")


@pytest.mark.asyncio
async def test_maps_authentication_failure():

    async def fake_generator(prompt):

        raise RuntimeError(
            "Gemini authentication failed."
        )

    provider = GeminiProvider(
        generator=fake_generator
    )

    with pytest.raises(LLMProviderAuthenticationError):

        await provider.generate("Explain networking.")


@pytest.mark.asyncio
async def test_maps_missing_configuration():

    async def fake_generator(prompt):

        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

    provider = GeminiProvider(
        generator=fake_generator
    )

    with pytest.raises(LLMProviderConfigurationError):

        await provider.generate("Explain algorithms.")


@pytest.mark.asyncio
async def test_maps_unknown_failure():

    async def fake_generator(prompt):

        raise RuntimeError(
            "Unknown Gemini failure."
        )

    provider = GeminiProvider(
        generator=fake_generator
    )

    with pytest.raises(LLMProviderExecutionError):

        await provider.generate("Explain algorithms.")