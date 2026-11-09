from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.chat_service import (
    generate_chat_response,
)


@pytest.mark.asyncio
async def test_chat_uses_rewritten_query_and_generator(
    monkeypatch,
):
    generator = AsyncMock(
        return_value=(
            "Binary search repeatedly divides a sorted search space."
        )
    )

    monkeypatch.setattr(
        "app.services.chat_service.evaluate_message",
        lambda message: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )

    monkeypatch.setattr(
        "app.services.chat_service.validate_output",
        lambda answer: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )

    result = await generate_chat_response(
        "Explain binary search.",
        llm_generator=generator,
    )

    generator.assert_awaited_once()

    assert isinstance(result, str)

    assert "Binary search" in result


@pytest.mark.asyncio
async def test_chat_rejects_unsafe_input_before_generation(
    monkeypatch,
):
    generator = AsyncMock()

    monkeypatch.setattr(
        "app.services.chat_service.evaluate_message",
        lambda message: SimpleNamespace(
            allowed=False,
            response="Request rejected.",
        ),
    )

    result = await generate_chat_response(
        "Unsafe request",
        llm_generator=generator,
    )

    assert result == "Request rejected."

    generator.assert_not_called()


@pytest.mark.asyncio
async def test_chat_rejects_unsafe_generated_output(
    monkeypatch,
):
    generator = AsyncMock(
        return_value="Generated answer."
    )

    monkeypatch.setattr(
        "app.services.chat_service.evaluate_message",
        lambda message: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )

    monkeypatch.setattr(
        "app.services.chat_service.validate_output",
        lambda answer: SimpleNamespace(
            allowed=False,
            response="Output blocked.",
        ),
    )

    result = await generate_chat_response(
        "Explain binary search.",
        llm_generator=generator,
    )

    assert result == "Output blocked."

    generator.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_rejects_invalid_generated_response():
    with pytest.raises(ValueError):
        await generate_chat_response(
            "   "
        )