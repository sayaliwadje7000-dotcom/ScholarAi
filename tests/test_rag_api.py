import uuid

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi.testclient import TestClient

from app.main import app

from app.api.dependencies import get_current_user
from app.api.rag_dependencies import get_rag_service

from app.database.session import get_db

from app.services.rag.rag_service import RAGResult


@pytest.fixture
def user():

    return SimpleNamespace(
        id=uuid.uuid4(),
        is_active=True,
    )


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def rag_result():

    return RAGResult(
        query="Explain binary search.",
        answer="Binary search is an efficient algorithm.",
        retrieved_chunks=[],
        total_retrieved=0,
        grounded=False,
        included_chunks=0,
        excluded_chunks=0,
        context_characters=0,
        citations=[],
        citation_issues=[],
        grounding_status="insufficient_evidence",
        grounding_report=None,
    )


@pytest.fixture
def client(user, mock_db, rag_result):

    rag_service = MagicMock()

    rag_service.ask = AsyncMock(
        return_value=rag_result
    )

    def override_current_user():
        return user

    def override_db():
        yield mock_db

    def override_rag_service():
        return rag_service

    app.dependency_overrides[get_current_user] = (
        override_current_user
    )

    app.dependency_overrides[get_db] = override_db

    app.dependency_overrides[get_rag_service] = (
        override_rag_service
    )

    with TestClient(app) as test_client:

        yield test_client, rag_service

    app.dependency_overrides.clear()


# ============================================================
# AUTHENTICATION
# ============================================================

def test_rag_endpoint_requires_authentication():

    with TestClient(app) as test_client:

        response = test_client.post(
            "/api/v1/rag/ask",
            json={
                "query": "Explain binary search."
            },
        )

    assert response.status_code == 501


# ============================================================
# SUCCESSFUL REQUEST
# ============================================================

def test_rag_endpoint_success(client, user):

    test_client, rag_service = client

    response = test_client.post(
        "/api/v1/rag/ask",
        json={
            "query": "Explain binary search."
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "Explain binary search."

    assert data["answer"] == (
        "Binary search is an efficient algorithm."
    )

    assert data["grounding_status"] == (
        "insufficient_evidence"
    )

    rag_service.ask.assert_awaited_once()

    call_kwargs = rag_service.ask.await_args.kwargs

    assert call_kwargs["user_id"] == user.id


# ============================================================
# INVALID REQUEST
# ============================================================

def test_rag_endpoint_rejects_empty_query(client):

    test_client, rag_service = client

    response = test_client.post(
        "/api/v1/rag/ask",
        json={
            "query": ""
        },
    )

    assert response.status_code == 422

    rag_service.ask.assert_not_awaited()


def test_rag_endpoint_rejects_invalid_limit(client):

    test_client, rag_service = client

    response = test_client.post(
        "/api/v1/rag/ask",
        json={
            "query": "Explain binary search.",
            "limit": 1000,
        },
    )

    assert response.status_code == 422

    rag_service.ask.assert_not_awaited()


# ============================================================
# SERVICE FAILURE
# ============================================================

def test_rag_endpoint_handles_service_unavailability(client):

    test_client, rag_service = client

    rag_service.ask.side_effect = RuntimeError(
        "Provider unavailable."
    )

    response = test_client.post(
        "/api/v1/rag/ask",
        json={
            "query": "Explain binary search."
        },
    )

    assert response.status_code == 503

    assert response.json()["detail"] == (
        "The RAG service is temporarily unavailable."
    )


# ============================================================
# RESPONSE CONTRACT
# ============================================================

def test_rag_response_contains_required_fields(client):

    test_client, _ = client

    response = test_client.post(
        "/api/v1/rag/ask",
        json={
            "query": "Explain binary search."
        },
    )

    assert response.status_code == 200

    data = response.json()

    required_fields = {
        "query",
        "answer",
        "retrieved_chunks",
        "total_retrieved",
        "grounded",
        "included_chunks",
        "excluded_chunks",
        "context_characters",
        "citations",
        "citation_issues",
        "grounding_status",
        "grounding_report",
    }

    assert required_fields.issubset(data.keys())