from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import generate_chat_response


router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask ScholarAI a question",
    description=(
        "Accepts a student's academic question and returns an "
        "AI-generated response using the locally running Ollama model."
    ),
)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process an academic question using the LLM service."""

    try:
        answer = await generate_chat_response(request.message)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return ChatResponse(
        answer=answer,
        conversation_id=request.conversation_id,
        status="success",
    )