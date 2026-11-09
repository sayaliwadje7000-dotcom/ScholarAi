"""
ScholarAI Conversation Context Schemas.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ConversationContextMessage(BaseModel):
    """
    A validated message selected for LLM context.
    """

    role: Literal["user", "assistant"]

    content: str = Field(
        min_length=1,
        max_length=12000,
    )

    token_estimate: int = Field(
        ge=0,
    )

    created_at: datetime | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "Conversation message cannot be empty."
            )

        return value


class ConversationContextResult(BaseModel):
    """
    Result produced by the context management service.
    """

    conversation_id: str

    messages: list[ConversationContextMessage]

    estimated_tokens: int = Field(
        ge=0,
    )

    included_messages: int = Field(
        ge=0,
    )

    excluded_messages: int = Field(
        ge=0,
    )

    context_truncated: bool

    max_context_tokens: int = Field(
        gt=0,
    )