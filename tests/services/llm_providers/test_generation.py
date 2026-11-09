from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.llm_providers import generation


@pytest.mark.asyncio
async def test_generation_adapter_returns_response(
    monkeypatch,
):
    router_generate = AsyncMock(
        return_value=SimpleNamespace(
            response="Academic answer.",
        )
    )

    monkeypatch.setattr(
        generation.llm_provider_router,
        "generate",
        router_generate,
    )

    result = await generation.generate_with_provider_router(
        "Explain binary search."
    )

    assert result == "Academic answer."

    router_generate.assert_awaited_once_with(
        prompt="Explain binary search."
    )


@pytest.mark.asyncio
async def test_generation_adapter_rejects_empty_prompt():
    with pytest.raises(ValueError):
        await generation.generate_with_provider_router(
            "   "
        )


@pytest.mark.asyncio
async def test_generation_adapter_rejects_empty_provider_response(
    monkeypatch,
):
    router_generate = AsyncMock(
        return_value=SimpleNamespace(
            response="   ",
        )
    )

    monkeypatch.setattr(
        generation.llm_provider_router,
        "generate",
        router_generate,
    )

    with pytest.raises(RuntimeError):
        await generation.generate_with_provider_router(
            "Explain binary search."
        )