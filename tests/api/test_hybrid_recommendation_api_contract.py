from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.hybrid_recommendations import router
from app.api.dependencies import get_current_user

from app.api.hybrid_recommendation_dependencies import (
    get_hybrid_recommendation_orchestrator,
)


def make_fake_orchestrator(user_id):
    """
    Create a deterministic fake implementing the API's
    orchestration dependency contract.

    This is an API boundary test, not a real engine test.
    """

    request_id = uuid4()

    return SimpleNamespace(
        execute=lambda context, **kwargs: SimpleNamespace(
            request_id=request_id,
            user_id=user_id,
            generated_at=datetime.now(timezone.utc),
            ranked_candidates=(),
            component_reports=(),
            total_candidates_discovered=0,
            total_candidates_after_deduplication=0,
            total_candidates_scored=0,
            total_candidates_accepted=0,
            total_candidates_returned=0,
            duration_ms=1.0,
            fallback_used=False,
            warnings=(),
        )
    )


def create_test_client(user_id):
    app = FastAPI()

    app.include_router(
        router,
        prefix="/api/v1",
    )

    fake_orchestrator = make_fake_orchestrator(user_id)

    app.dependency_overrides[
        get_hybrid_recommendation_orchestrator
    ] = lambda: fake_orchestrator
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=user_id, is_active=True)
    )

    return TestClient(app)


def test_hybrid_api_returns_valid_empty_response():
    user_id = uuid4()
    client = create_test_client(user_id)

    response = client.post(
        "/api/v1/recommendations/hybrid",
        json={
            "query": "Python data structures",
            "limit": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["user_id"] == str(user_id)
    assert body["recommendations"] == []
    assert body["total_candidates_returned"] == 0
    assert body["fallback_used"] is False


def test_hybrid_api_rejects_invalid_request():
    user_id = uuid4()
    client = create_test_client(user_id)

    response = client.post(
        "/api/v1/recommendations/hybrid",
        json={
            "query": "",
            "limit": 5,
        },
    )

    assert response.status_code == 422


def test_hybrid_api_rejects_excessive_limit():
    user_id = uuid4()
    client = create_test_client(user_id)

    response = client.post(
        "/api/v1/recommendations/hybrid",
        json={
            "query": "Python",
            "limit": 1000,
        },
    )

    assert response.status_code == 422