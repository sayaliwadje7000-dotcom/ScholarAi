from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services import chat_service


@pytest.mark.asyncio
async def test_chat_service_invokes_query_classifier(monkeypatch):

    classifier = Mock()

    classifier.classify.return_value = SimpleNamespace(
        intent=SimpleNamespace(
            value="academic_learning"
        ),
        task_type=SimpleNamespace(
            value="explanation"
        ),
        confidence=0.90,
        suggested_workflow="academic_response",
        ambiguous=False,
        classifier_version="1.0.0",
    )

    llm = AsyncMock(
        return_value="Binary search is a searching algorithm."
    )

    monkeypatch.setattr(
        chat_service,
        "query_classification_service",
        classifier,
    )

    monkeypatch.setattr(
        chat_service,
        "generate_llm_response",
        llm,
    )

    monkeypatch.setattr(
        chat_service,
        "evaluate_message",
        lambda message: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )

    monkeypatch.setattr(
        chat_service,
        "validate_output",
        lambda answer: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )

    result = await chat_service.generate_chat_response(
        "Explain binary search."
    )

    assert result == "Binary search is a searching algorithm."

    classifier.classify.assert_called_once_with(
        query="Explain binary search.",
        has_conversation_context=False,
        has_document_context=False,
    )

    llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_safety_rejection_prevents_classification(monkeypatch):

    classifier = Mock()

    monkeypatch.setattr(
        chat_service,
        "query_classification_service",
        classifier,
    )

    monkeypatch.setattr(
        chat_service,
        "evaluate_message",
        lambda message: SimpleNamespace(
            allowed=False,
            response="Request rejected.",
        ),
    )

    result = await chat_service.generate_chat_response(
        "Unsafe request"
    )

    assert result == "Request rejected."

    classifier.classify.assert_not_called()


@pytest.mark.asyncio
async def test_chat_service_returns_existing_llm_answer(monkeypatch):

    monkeypatch.setattr(
        chat_service,
        "evaluate_message",
        lambda message: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )

    monkeypatch.setattr(
        chat_service,
        "validate_output",
        lambda answer: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )

    monkeypatch.setattr(
        chat_service,
        "generate_llm_response",
        AsyncMock(return_value="Academic answer."),
    )

    result = await chat_service.generate_chat_response(
        "Explain artificial intelligence."
    )

    assert result == "Academic answer."