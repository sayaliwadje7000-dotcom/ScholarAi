import uuid

from datetime import datetime, timezone

import pytest

from types import SimpleNamespace

from app.core.conversation_context_config import (
    ConversationContextSettings,
)

from app.services.conversation_context_service import (
    ConversationContextService,
    ConversationContextValidationError,
)


@pytest.fixture
def settings():

    return ConversationContextSettings(
        max_history_messages=20,
        max_context_tokens=100,
        max_message_characters=12000,
        estimated_characters_per_token=4,
    )


@pytest.fixture
def service(settings):

    return ConversationContextService(
        settings=settings
    )


def make_message(
    role,
    content,
    created_at=None,
):

    return SimpleNamespace(
        role=role,
        content=content,
        created_at=(
            created_at
            or datetime.now(timezone.utc)
        ),
    )


# ==========================================================
# TOKEN ESTIMATION
# ==========================================================

def test_estimates_tokens(service):

    assert service.estimate_tokens(
        "12345678"
    ) == 2


def test_empty_string_has_zero_tokens(service):

    assert service.estimate_tokens("") == 0


def test_token_estimation_rejects_invalid_type(service):

    with pytest.raises(
        ConversationContextValidationError
    ):

        service.estimate_tokens(None)


# ==========================================================
# CONTEXT CONSTRUCTION
# ==========================================================

def test_builds_context_from_messages(service):

    conversation_id = uuid.uuid4()

    messages = [
        make_message(
            "user",
            "Explain binary search.",
        ),
        make_message(
            "assistant",
            "Binary search is an efficient searching algorithm.",
        ),
    ]

    result = service.build_context(
        conversation_id,
        messages,
    )

    assert result.conversation_id == str(
        conversation_id
    )

    assert result.included_messages == 2

    assert result.excluded_messages == 0

    assert result.context_truncated is False


def test_preserves_chronological_order(service):

    conversation_id = uuid.uuid4()

    first = make_message(
        "user",
        "First question",
    )

    second = make_message(
        "assistant",
        "First answer",
    )

    third = make_message(
        "user",
        "Second question",
    )

    result = service.build_context(
        conversation_id,
        [first, second, third],
    )

    assert [
        message.content
        for message in result.messages
    ] == [
        "First question",
        "First answer",
        "Second question",
    ]


def test_excludes_system_messages(service):

    conversation_id = uuid.uuid4()

    messages = [
        make_message(
            "system",
            "Internal system instruction",
        ),
        make_message(
            "user",
            "Explain operating systems.",
        ),
    ]

    result = service.build_context(
        conversation_id,
        messages,
    )

    assert result.included_messages == 1

    assert result.messages[0].role == "user"


# ==========================================================
# TOKEN BUDGET
# ==========================================================

def test_enforces_context_token_budget(service):

    conversation_id = uuid.uuid4()

    messages = [
        make_message(
            "user",
            "A" * 200,
        ),
        make_message(
            "assistant",
            "B" * 200,
        ),
        make_message(
            "user",
            "C" * 200,
        ),
    ]

    result = service.build_context(
        conversation_id,
        messages,
    )

    assert result.estimated_tokens <= 100

    assert result.context_truncated is True

    assert result.included_messages < 3

    assert result.excluded_messages > 0
def test_prioritizes_recent_messages(service):

    conversation_id = uuid.uuid4()

    messages = [
        make_message(
            "user",
            "A" * 200,
        ),
        make_message(
            "assistant",
            "B" * 200,
        ),
        make_message(
            "user",
            "Recent message",
        ),
    ]

    result = service.build_context(
        conversation_id,
        messages,
    )

    assert result.messages[-1].content == (
        "Recent message"
    )


def test_reports_excluded_messages(service):

    conversation_id = uuid.uuid4()

    messages = [
        make_message(
            "user",
            "A" * 200,
        ),
        make_message(
            "assistant",
            "B" * 200,
        ),
    ]

    result = service.build_context(
        conversation_id,
        messages,
    )

    assert result.excluded_messages == (
        len(messages) - result.included_messages
    )


# ==========================================================
# INPUT VALIDATION
# ==========================================================

def test_rejects_invalid_conversation_id(service):

    with pytest.raises(
        ConversationContextValidationError
    ):

        service.build_context(
            "invalid-uuid",
            [],
        )


def test_rejects_non_list_messages(service):

    with pytest.raises(
        ConversationContextValidationError
    ):

        service.build_context(
            uuid.uuid4(),
            None,
        )


def test_empty_context_is_valid(service):

    result = service.build_context(
        uuid.uuid4(),
        [],
    )

    assert result.included_messages == 0

    assert result.estimated_tokens == 0

    assert result.context_truncated is False


# ==========================================================
# MESSAGE VALIDATION
# ==========================================================

def test_ignores_empty_messages(service):

    result = service.build_context(
        uuid.uuid4(),
        [
            make_message("user", "   "),
            make_message("assistant", "Valid answer"),
        ],
    )

    assert result.included_messages == 1