from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The student's academic question.",
    )

    conversation_id: str | None = Field(
        default=None,
        description="The ID of an existing conversation, if available.",
    )


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str | None
    status: str