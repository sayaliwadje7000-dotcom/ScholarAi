from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.rag import get_current_user, get_db, get_rag_service


class FailingRAGService:
    async def ask(self, **kwargs):
        raise RuntimeError("Simulated internal RAG failure")


@pytest.fixture
def fault_tolerant_client():
    original_overrides = app.dependency_overrides.copy()

    def override_db():
        yield object()

    def override_current_user():
        return SimpleNamespace(id=1)

    def override_rag_service():
        return FailingRAGService()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_rag_service] = override_rag_service

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def get_rag_ask_path():
    matching_routes = [
        route
        for route in app.routes
        if getattr(route, "path", "").endswith("/ask")
        and "POST" in getattr(route, "methods", set())
    ]

    assert matching_routes, "POST RAG /ask endpoint was not registered."

    return matching_routes[0].path


def test_rag_api_handles_internal_service_failure(fault_tolerant_client):
    response = fault_tolerant_client.post(
        get_rag_ask_path(),
        json={
            "query": "Explain machine learning",
            "limit": 5,
        },
    )

    assert response.status_code == 503


def test_rag_api_failure_returns_json(fault_tolerant_client):
    response = fault_tolerant_client.post(
        get_rag_ask_path(),
        json={
            "query": "Explain database indexing",
            "limit": 5,
        },
    )

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
