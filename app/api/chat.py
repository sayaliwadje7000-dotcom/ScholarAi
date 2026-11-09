"""
ScholarAI Chat API.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)

from app.services.chat_service import (
    generate_chat_response,
)

from app.services.llm_providers.exceptions import (
    LLMProviderError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask ScholarAI a question",
    description=(
        "Accepts an academic question and returns an "
        "AI-generated response using ScholarAI's integrated "
        "LLM provider and response intelligence pipeline."
    ),
)
async def chat(
    request: ChatRequest,
) -> ChatResponse:
    """
    Process an academic question through the
    integrated ScholarAI chat workflow.
    """

    try:
        answer = await generate_chat_response(
            request.message
        )

    except LLMProviderError as exc:
        logger.exception(
            "LLM provider failure during chat generation."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "ScholarAI's response generation service "
                "is temporarily unavailable."
            ),
        ) from exc

    except RuntimeError as exc:
        logger.exception(
            "Chat generation failed."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return ChatResponse(
        answer=answer,
        conversation_id=request.conversation_id,
        status="success",
    )