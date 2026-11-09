"""
ScholarAI Conversation Context Management Service.

Provides secure conversation history retrieval and
bounded context-window construction.
"""

from __future__ import annotations

import math
import uuid

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.conversation_context_config import (
    conversation_context_settings,
)

from app.models.conversation import Conversation
from app.models.message import Message

from app.schemas.conversation_context import (
    ConversationContextMessage,
    ConversationContextResult,
)


# ==========================================================
# EXCEPTIONS
# ==========================================================

class ConversationContextError(Exception):
    """Base exception for context management."""


class ConversationNotFoundError(ConversationContextError):
    """Raised when the requested conversation is unavailable."""


class ConversationContextValidationError(
    ConversationContextError
):
    """Raised when context input is invalid."""


# ==========================================================
# INTERNAL MESSAGE REPRESENTATION
# ==========================================================

@dataclass(frozen=True)
class ContextCandidate:

    role: str

    content: str

    created_at: object | None

    token_estimate: int


# ==========================================================
# CONTEXT MANAGEMENT SERVICE
# ==========================================================

class ConversationContextService:
    """
    Retrieves and constructs bounded conversation history.

    Token counts are estimates, not provider-reported counts.
    """

    def __init__(self, settings=None):

        self.settings = (
            settings or conversation_context_settings
        )

    # ------------------------------------------------------
    # TOKEN ESTIMATION
    # ------------------------------------------------------

    def estimate_tokens(self, text: str) -> int:

        if not isinstance(text, str):
            raise ConversationContextValidationError(
                "Token estimation requires string input."
            )

        if not text:
            return 0

        characters_per_token = (
            self.settings.estimated_characters_per_token
        )

        return math.ceil(
            len(text) / characters_per_token
        )

    # ------------------------------------------------------
    # CONVERSATION OWNERSHIP
    # ------------------------------------------------------

    @staticmethod
    def _validate_uuid(value, field_name: str) -> uuid.UUID:

        try:
            return uuid.UUID(str(value))

        except (ValueError, TypeError, AttributeError) as exc:

            raise ConversationContextValidationError(
                f"{field_name} must be a valid UUID."
            ) from exc

    def _get_owned_conversation(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Conversation:

        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.is_archived.is_(False),
        )

        conversation = db.execute(
            statement
        ).scalar_one_or_none()

        if conversation is None:

            raise ConversationNotFoundError(
                "Conversation was not found or is not accessible."
            )

        return conversation

    # ------------------------------------------------------
    # MESSAGE RETRIEVAL
    # ------------------------------------------------------

    def _load_messages(
        self,
        db: Session,
        conversation_id: uuid.UUID,
    ) -> list[Message]:

        statement = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.role.in_(["user", "assistant"]),
            )
            .order_by(
                Message.created_at.desc(),
                Message.id.desc(),
            )
            .limit(
                self.settings.max_history_messages
            )
        )

        messages = list(
            db.execute(statement).scalars().all()
        )

        # Database retrieval is newest-first.
        # LLM context must be chronological.

        messages.reverse()

        return messages

    # ------------------------------------------------------
    # CANDIDATE VALIDATION
    # ------------------------------------------------------

    def _prepare_candidates(
        self,
        messages: list[Message],
    ) -> list[ContextCandidate]:

        candidates = []

        for message in messages:

            if message.role not in {
                "user",
                "assistant",
            }:
                continue

            if not isinstance(message.content, str):
                continue

            content = message.content.strip()

            if not content:
                continue

            if len(content) > (
                self.settings.max_message_characters
            ):
                content = content[
                    -self.settings.max_message_characters:
                ]

            token_estimate = self.estimate_tokens(
                content
            )

            candidates.append(
                ContextCandidate(
                    role=message.role,
                    content=content,
                    created_at=message.created_at,
                    token_estimate=token_estimate,
                )
            )

        return candidates

    # ------------------------------------------------------
    # CONTEXT WINDOW CONSTRUCTION
    # ------------------------------------------------------

    def _select_context_messages(
        self,
        candidates: list[ContextCandidate],
    ) -> tuple[list[ContextCandidate], int]:

        selected = []

        total_tokens = 0

        excluded_messages = 0

        budget = self.settings.max_context_tokens

        # Select newest messages first to prioritize
        # recent conversational context.

        for candidate in reversed(candidates):

            if (
                total_tokens + candidate.token_estimate
                > budget
            ):

                excluded_messages += 1
                continue

            selected.append(candidate)

            total_tokens += candidate.token_estimate

        # Restore chronological order.

        selected.reverse()

        return selected, excluded_messages

    # ------------------------------------------------------
    # PUBLIC CONTEXT BUILDER
    # ------------------------------------------------------

    def build_context(
        self,
        conversation_id,
        messages: list[Message],
    ) -> ConversationContextResult:

        conversation_uuid = self._validate_uuid(
            conversation_id,
            "Conversation ID",
        )

        if not isinstance(messages, list):

            raise ConversationContextValidationError(
                "Messages must be provided as a list."
            )

        candidates = self._prepare_candidates(
            messages
        )

        selected, budget_excluded = (
            self._select_context_messages(
                candidates
            )
        )

        context_messages = [
            ConversationContextMessage(
                role=message.role,
                content=message.content,
                token_estimate=message.token_estimate,
                created_at=message.created_at,
            )
            for message in selected
        ]

        estimated_tokens = sum(
            message.token_estimate
            for message in context_messages
        )

        excluded_messages = (
            len(messages) - len(selected)
        )

        return ConversationContextResult(
            conversation_id=str(conversation_uuid),

            messages=context_messages,

            estimated_tokens=estimated_tokens,

            included_messages=len(context_messages),

            excluded_messages=excluded_messages,

            context_truncated=excluded_messages > 0,

            max_context_tokens=(
                self.settings.max_context_tokens
            ),
        )

    # ------------------------------------------------------
    # DATABASE-BACKED CONTEXT RETRIEVAL
    # ------------------------------------------------------

    def get_conversation_context(
        self,
        db: Session,
        conversation_id,
        user_id,
    ) -> ConversationContextResult:

        conversation_uuid = self._validate_uuid(
            conversation_id,
            "Conversation ID",
        )

        user_uuid = self._validate_uuid(
            user_id,
            "User ID",
        )

        self._get_owned_conversation(
            db=db,
            conversation_id=conversation_uuid,
            user_id=user_uuid,
        )

        messages = self._load_messages(
            db=db,
            conversation_id=conversation_uuid,
        )

        return self.build_context(
            conversation_id=conversation_uuid,
            messages=messages,
        )


# ==========================================================
# SERVICE INSTANCE
# ==========================================================

conversation_context_service = (
    ConversationContextService()
)