from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import llm_service
from app.services.llm_service import (
    GEMINI_MODEL,
    SCHOLARAI_SYSTEM_PROMPT,
    generate_llm_response,
)


# ============================================================
# PROMPT ENGINEERING TESTS
# ============================================================

def test_system_prompt_identifies_scholarai_as_academic_tutor():
    assert "ScholarAI" in SCHOLARAI_SYSTEM_PROMPT
    assert "academic tutor" in SCHOLARAI_SYSTEM_PROMPT


def test_system_prompt_covers_comparison_questions():
    assert "COMPARISON QUESTIONS" in SCHOLARAI_SYSTEM_PROMPT
    assert "Markdown table" in SCHOLARAI_SYSTEM_PROMPT


def test_system_prompt_covers_problem_solving():
    assert "PROBLEM SOLVING" in SCHOLARAI_SYSTEM_PROMPT
    assert "step by step" in SCHOLARAI_SYSTEM_PROMPT


def test_system_prompt_covers_engineering_and_computer_science():
    assert "ENGINEERING AND COMPUTER SCIENCE" in SCHOLARAI_SYSTEM_PROMPT
    assert "time and space complexity" in SCHOLARAI_SYSTEM_PROMPT


def test_system_prompt_discourages_fabricated_information():
    assert "Never invent facts" in SCHOLARAI_SYSTEM_PROMPT
    assert "Acknowledge uncertainty" in SCHOLARAI_SYSTEM_PROMPT


# ============================================================
# INPUT VALIDATION TESTS
# ============================================================

@pytest.mark.parametrize(
    "message",
    ["", " ", "\n\t"],
)
@pytest.mark.asyncio
async def test_rejects_empty_messages(message):
    with pytest.raises(ValueError, match="Message cannot be empty"):
        await generate_llm_response(message)


@pytest.mark.asyncio
async def test_rejects_invalid_message_type():
    with pytest.raises(ValueError, match="Message cannot be empty"):
        await generate_llm_response(None)


# ============================================================
# MOCKED GEMINI CLIENT
# ============================================================

def create_mock_gemini_client(answer="Academic answer."):
    mock_response = MagicMock()
    mock_response.text = answer

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=mock_response
    )

    return mock_client, mock_response


# ============================================================
# GEMINI RESPONSE TESTS
# ============================================================

@pytest.mark.asyncio
async def test_generate_llm_response_returns_answer():
    mock_client, _ = create_mock_gemini_client(
        "Machine learning learns patterns from data."
    )

    with patch(
        "app.services.llm_service._create_gemini_client",
        return_value=mock_client,
    ):
        answer = await generate_llm_response(
            "Explain machine learning."
        )

    assert answer == "Machine learning learns patterns from data."


@pytest.mark.asyncio
async def test_generate_llm_response_strips_whitespace():
    mock_client, _ = create_mock_gemini_client(
        "  Academic answer.  \n"
    )

    with patch(
        "app.services.llm_service._create_gemini_client",
        return_value=mock_client,
    ):
        answer = await generate_llm_response(
            "Explain a concept."
        )

    assert answer == "Academic answer."


@pytest.mark.asyncio
async def test_request_uses_configured_model_and_prompt():
    mock_client, _ = create_mock_gemini_client()

    with patch(
        "app.services.llm_service._create_gemini_client",
        return_value=mock_client,
    ):
        await generate_llm_response(
            "Compare machine learning and deep learning."
        )

    mock_client.aio.models.generate_content.assert_awaited_once()

    call_arguments = (
        mock_client.aio.models.generate_content.await_args
    )

    assert call_arguments.kwargs["model"] == GEMINI_MODEL

    assert (
        call_arguments.kwargs["contents"]
        == "Compare machine learning and deep learning."
    )

    config = call_arguments.kwargs["config"]

    assert config.system_instruction == SCHOLARAI_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_generate_llm_response_rejects_empty_answer():
    mock_client, _ = create_mock_gemini_client("   ")

    with patch(
        "app.services.llm_service._create_gemini_client",
        return_value=mock_client,
    ):
        with pytest.raises(RuntimeError, match="empty response"):
            await generate_llm_response(
                "Explain machine learning."
            )


@pytest.mark.asyncio
async def test_generate_llm_response_rejects_invalid_response():
    mock_client, mock_response = create_mock_gemini_client()
    mock_response.text = None

    with patch(
        "app.services.llm_service._create_gemini_client",
        return_value=mock_client,
    ):
        with pytest.raises(RuntimeError, match="invalid response"):
            await generate_llm_response(
                "Explain machine learning."
            )


@pytest.mark.asyncio
async def test_generate_llm_response_rejects_incomplete_answer():
    mock_client, _ = create_mock_gemini_client("A")

    with patch(
        "app.services.llm_service._create_gemini_client",
        return_value=mock_client,
    ):
        with pytest.raises(RuntimeError, match="incomplete response"):
            await generate_llm_response(
                "Explain machine learning."
            )


# ============================================================
# GEMINI ERROR HANDLING TESTS
# ============================================================

@pytest.mark.parametrize(
    "api_error, expected_message",
    [
        ("429 resource_exhausted", "usage limit reached"),
        ("503 unavailable", "temporarily unavailable"),
        ("401 unauthorized", "authentication failed"),
        ("403 permission denied", "access was denied"),
        ("404 not_found", "unavailable"),
    ],
)
@pytest.mark.asyncio
async def test_generate_llm_response_handles_api_errors(
    api_error,
    expected_message,
):
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception(api_error)
    )

    with patch(
        "app.services.llm_service._create_gemini_client",
        return_value=mock_client,
    ):
        with pytest.raises(RuntimeError, match=expected_message):
            await generate_llm_response(
                "Explain machine learning."
            )


@pytest.mark.asyncio
async def test_generate_llm_response_handles_unexpected_error():
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("Unexpected failure")
    )

    with patch(
        "app.services.llm_service._create_gemini_client",
        return_value=mock_client,
    ):
        with pytest.raises(
            RuntimeError,
            match="could not obtain a response",
        ):
            await generate_llm_response(
                "Explain machine learning."
            )


# ============================================================
# CONFIGURATION VALIDATION TESTS
# ============================================================

@pytest.mark.asyncio
async def test_rejects_missing_api_key():
    with patch.object(llm_service, "GEMINI_API_KEY", ""):
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY is missing"):
            await generate_llm_response(
                "Explain machine learning."
            )


@pytest.mark.asyncio
async def test_rejects_invalid_timeout():
    with patch.object(llm_service, "GEMINI_TIMEOUT_SECONDS", 0):
        with pytest.raises(RuntimeError, match="TIMEOUT_SECONDS"):
            await generate_llm_response(
                "Explain machine learning."
            )


@pytest.mark.asyncio
async def test_rejects_invalid_temperature():
    with patch.object(llm_service, "GEMINI_TEMPERATURE", 3):
        with pytest.raises(RuntimeError, match="TEMPERATURE"):
            await generate_llm_response(
                "Explain machine learning."
            )


@pytest.mark.asyncio
async def test_rejects_invalid_max_output_tokens():
    with patch.object(llm_service, "GEMINI_MAX_OUTPUT_TOKENS", 0):
        with pytest.raises(RuntimeError, match="MAX_OUTPUT_TOKENS"):
            await generate_llm_response(
                "Explain machine learning."
            )
