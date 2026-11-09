"""
ScholarAI Conversation Context Configuration.

Controls conversation history retrieval and context-window
budgeting for advanced LLM workflows.
"""

from dataclasses import dataclass
import math
import os


def _positive_integer(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be a valid integer."
        ) from exc

    if value <= 0:
        raise ValueError(
            f"{name} must be greater than zero."
        )

    return value


@dataclass(frozen=True)
class ConversationContextSettings:
    """
    Immutable settings for conversation context management.
    """

    max_history_messages: int
    max_context_tokens: int
    max_message_characters: int
    estimated_characters_per_token: int


def load_conversation_context_settings(
) -> ConversationContextSettings:

    settings = ConversationContextSettings(
        max_history_messages=_positive_integer(
            "SCHOLARAI_MAX_HISTORY_MESSAGES",
            20,
        ),

        max_context_tokens=_positive_integer(
            "SCHOLARAI_MAX_CONTEXT_TOKENS",
            6000,
        ),

        max_message_characters=_positive_integer(
            "SCHOLARAI_MAX_HISTORY_MESSAGE_CHARACTERS",
            12000,
        ),

        estimated_characters_per_token=_positive_integer(
            "SCHOLARAI_CHARACTERS_PER_TOKEN",
            4,
        ),
    )

    return settings


conversation_context_settings = (
    load_conversation_context_settings()
)