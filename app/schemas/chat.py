
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The student's academic question.",
    )

    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        description="The ID of an existing conversation, if available.",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Message cannot contain only whitespace.")

        return value

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = value.strip()

            if not value:
                raise ValueError(
                    "Conversation ID cannot contain only whitespace."
                )

        return value


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str | None
    status: str

