from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.hybrid_recommendations import router
from app.api.dependencies import get_current_user
from types import SimpleNamespace
from app.api.hybrid_recommendation_dependencies import (
    get_hybrid_recommendation_orchestrator,
)


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def app(user_id):
    application = FastAPI()

    application.include_router(
        router,
        prefix="/api/v1",
    )

    application.state.hybrid_recommendation_orchestrator = (
        object()
    )

    application.dependency_overrides[
        get_hybrid_recommendation_orchestrator
    ] = lambda: application.state.hybrid_recommendation_orchestrator
    application.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=user_id, is_active=True)
    )

    yield application

    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)


def test_hybrid_endpoint_is_registered(client):
    response = client.post(
        "/api/v1/recommendations/hybrid",
        json={
            "query": "Python data structures",
            "limit": 5,
        },
    )

    # The dependency is deliberately a placeholder object here.
    # The endpoint must reject it rather than treating it as
    # a working recommendation orchestrator.
    assert response.status_code in {
        500,
        503,
    }


def test_hybrid_request_rejects_empty_query(client):
    response = client.post(
        "/api/v1/recommendations/hybrid",
        json={
            "query": "",
        },
    )

    assert response.status_code == 422


def test_hybrid_request_rejects_missing_query(client):
    response = client.post(
        "/api/v1/recommendations/hybrid",
        json={
            "limit": 5,
        },
    )

    assert response.status_code == 422


def test_hybrid_request_rejects_invalid_limit(client):
    response = client.post(
        "/api/v1/recommendations/hybrid",
        json={
            "query": "Python",
            "limit": 1000,
        },
    )

    assert response.status_code == 422


def test_hybrid_request_rejects_unknown_fields(client):
    response = client.post(
        "/api/v1/recommendations/hybrid",
        json={
            "query": "Python",
            "unknown_field": "not-supported",
        },
    )

    assert response.status_code == 422


def test_hybrid_request_accepts_valid_payload_schema(client):
    response = client.post(
        "/api/v1/recommendations/hybrid",
        json={
            "query": "Python data structures",
            "filters": {
                "resource_type": "article",
            },
            "metadata": {
                "source": "study_dashboard",
            },
            "limit": 5,
        },
    )

    assert response.status_code in {
        500,
        503,
    }