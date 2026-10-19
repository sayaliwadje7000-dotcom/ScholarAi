from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import generate_chat_response


router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask ScholarAI a question",
    description=(
        "Accepts a student's academic question and returns a response. "
        "Currently uses a temporary placeholder service; LLM integration "
        "will be added in Phase 5."
    ),
)
def chat(request: ChatRequest) -> ChatResponse:
    """Process an academic question and return a response."""

    answer = generate_chat_response(request.message)

    return ChatResponse(
        answer=answer,
        conversation_id=request.conversation_id,
        status="success",
    )