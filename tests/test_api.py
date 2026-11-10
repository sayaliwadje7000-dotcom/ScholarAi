from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
import uuid
from types import SimpleNamespace

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.services.role_service import role_service

client = TestClient(app)
@pytest.fixture(autouse=True)
def authenticated_test_user(monkeypatch):
    user = SimpleNamespace(
        id=uuid.uuid4(),
        is_active=True,
    )

    previous_overrides = dict(app.dependency_overrides)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: object()

    monkeypatch.setattr(
        role_service,
        "get_user_roles",
        lambda db, user_id: {"student"},
    )

    yield

    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)

# ---------------------------------------------------------
# HOME AND HEALTH ENDPOINT TESTS
# ---------------------------------------------------------

def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["application"] == "ScholarAI"
    assert data["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# ---------------------------------------------------------
# CHAT ENDPOINT TESTS
# ---------------------------------------------------------

@patch(
    "app.api.chat.generate_chat_response",
    new_callable=AsyncMock,
)
def test_chat_endpoint(mock_generate):
    mock_generate.return_value = (
        "Machine learning enables computers to learn patterns "
        "from data and make predictions."
    )

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Explain machine learning.",
            "conversation_id": None,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["answer"] == (
        "Machine learning enables computers to learn patterns "
        "from data and make predictions."
    )
    assert data["conversation_id"] is None

    mock_generate.assert_awaited_once_with(
        "Explain machine learning."
    )


@patch(
    "app.api.chat.generate_chat_response",
    new_callable=AsyncMock,
)
def test_chat_strips_message_whitespace(mock_generate):
    mock_generate.return_value = "This is a test answer."

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "   Explain machine learning.   ",
            "conversation_id": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "This is a test answer."

    mock_generate.assert_awaited_once_with(
        "Explain machine learning."
    )


@patch(
    "app.api.chat.generate_chat_response",
    new_callable=AsyncMock,
)
def test_chat_preserves_conversation_id(mock_generate):
    mock_generate.return_value = "This is a test answer."

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Explain neural networks.",
            "conversation_id": "conversation-123",
        },
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == "conversation-123"


@patch(
    "app.api.chat.generate_chat_response",
    new_callable=AsyncMock,
)
def test_chat_returns_generated_answer(mock_generate):
    expected_answer = (
        "A neural network is a computational model inspired "
        "by interconnected neurons."
    )

    mock_generate.return_value = expected_answer

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "What is a neural network?",
            "conversation_id": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == expected_answer


# ---------------------------------------------------------
# INPUT VALIDATION TESTS
# ---------------------------------------------------------

def test_chat_rejects_empty_message():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "",
            "conversation_id": None,
        },
    )

    assert response.status_code == 422


def test_chat_rejects_invalid_message_type():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": 123,
            "conversation_id": None,
        },
    )

    assert response.status_code == 422


def test_chat_rejects_whitespace_only_message():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "     ",
            "conversation_id": None,
        },
    )

    assert response.status_code == 422


def test_chat_rejects_message_exceeding_max_length():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "a" * 5001,
            "conversation_id": None,
        },
    )

    assert response.status_code == 422


def test_chat_rejects_whitespace_only_conversation_id():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Explain machine learning.",
            "conversation_id": "     ",
        },
    )

    assert response.status_code == 422


def test_chat_validation_error_response_structure():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "",
            "conversation_id": None,
        },
    )

    assert response.status_code == 422

    data = response.json()

    assert "detail" in data
    assert isinstance(data["detail"], list)
    assert len(data["detail"]) > 0

    error = data["detail"][0]

    assert error["loc"] == ["body", "message"]
    assert error["type"] == "string_too_short"


# ---------------------------------------------------------
# LLM ERROR-HANDLING TESTS
# ---------------------------------------------------------

@patch(
    "app.api.chat.generate_chat_response",
    new_callable=AsyncMock,
)
def test_chat_returns_503_when_llm_is_unavailable(mock_generate):
    mock_generate.side_effect = RuntimeError(
        "Cannot connect to Ollama. Ensure Ollama is running."
    )

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Explain machine learning.",
            "conversation_id": None,
        },
    )

    assert response.status_code == 503

    data = response.json()

    assert data["detail"] == (
        "Cannot connect to Ollama. Ensure Ollama is running."
    )


@patch(
    "app.api.chat.generate_chat_response",
    new_callable=AsyncMock,
)
def test_chat_returns_503_when_llm_times_out(mock_generate):
    mock_generate.side_effect = RuntimeError(
        "The AI model took too long to respond. Please try again."
    )

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Explain neural networks.",
            "conversation_id": None,
        },
    )

    assert response.status_code == 503

    assert "too long to respond" in response.json()["detail"]


# ---------------------------------------------------------
# CORS TESTS
# ---------------------------------------------------------

def test_cors_allows_local_frontend_origin():
    response = client.options(
        "/api/v1/chat",
        headers={
            "Origin": "http://127.0.0.1:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200

    assert (
        response.headers["access-control-allow-origin"]
        == "http://127.0.0.1:5500"
    )


def test_cors_allows_localhost_frontend_origin():
    response = client.options(
        "/api/v1/chat",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200

    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:5500"
    )


def test_cors_rejects_unconfigured_origin():
    response = client.options(
        "/api/v1/chat",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert (
        "access-control-allow-origin"
        not in response.headers
    )