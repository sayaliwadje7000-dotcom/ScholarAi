from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user

from app.api.ml_recommendation_dependencies import (
    get_ml_recommendation_service,
)

from app.api.ml_recommendations import router

from app.services.recommendations.ml.inference.inference_exceptions import (
    ModelNotAvailableError,
)


USER_ID = uuid4()
RESOURCE_ID_1 = uuid4()
RESOURCE_ID_2 = uuid4()


class FakeMLRecommendationService:

    def __init__(self):
        self.calls = []

    def predict(
        self,
        user_id,
        resource_ids,
        prediction_at,
    ):
        self.calls.append(
            {
                "user_id": user_id,
                "resource_ids": resource_ids,
                "prediction_at": prediction_at,
            }
        )

        return SimpleNamespace(
            model_run_id="test-run-001",
            predictions=[
                SimpleNamespace(
                    resource_id=RESOURCE_ID_1,
                    relevance_probability=0.92,
                    is_relevant=True,
                ),
                SimpleNamespace(
                    resource_id=RESOURCE_ID_2,
                    relevance_probability=0.31,
                    is_relevant=False,
                ),
            ],
        )


@pytest.fixture
def service():
    return FakeMLRecommendationService()


@pytest.fixture
def client(service):

    app = FastAPI()

    app.include_router(
        router,
        prefix="/api/v1/recommendations",
    )

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=USER_ID)
    )

    app.dependency_overrides[
        get_ml_recommendation_service
    ] = lambda: service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_ml_recommendation_endpoint_returns_predictions(
    client,
):
    response = client.post(
        "/api/v1/recommendations/ml",
        json={
            "resource_ids": [
                str(RESOURCE_ID_1),
                str(RESOURCE_ID_2),
            ]
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["user_id"] == str(USER_ID)

    assert payload["model_run_id"] == "test-run-001"

    assert payload["total_results"] == 2

    assert len(payload["recommendations"]) == 2


def test_ml_recommendation_preserves_candidate_order(
    client,
):
    response = client.post(
        "/api/v1/recommendations/ml",
        json={
            "resource_ids": [
                str(RESOURCE_ID_1),
                str(RESOURCE_ID_2),
            ]
        },
    )

    payload = response.json()

    returned_ids = [
        item["resource_id"]
        for item in payload["recommendations"]
    ]

    assert returned_ids == [
        str(RESOURCE_ID_1),
        str(RESOURCE_ID_2),
    ]


def test_ml_recommendation_rejects_empty_resource_list(
    client,
):
    response = client.post(
        "/api/v1/recommendations/ml",
        json={
            "resource_ids": [],
        },
    )

    assert response.status_code == 422


def test_ml_recommendation_rejects_duplicate_resources(
    client,
):
    response = client.post(
        "/api/v1/recommendations/ml",
        json={
            "resource_ids": [
                str(RESOURCE_ID_1),
                str(RESOURCE_ID_1),
            ]
        },
    )

    assert response.status_code == 422


def test_ml_recommendation_rejects_invalid_uuid(
    client,
):
    response = client.post(
        "/api/v1/recommendations/ml",
        json={
            "resource_ids": ["not-a-valid-uuid"],
        },
    )

    assert response.status_code == 422


def test_ml_recommendation_rejects_naive_timestamp(
    client,
):
    response = client.post(
        "/api/v1/recommendations/ml",
        json={
            "resource_ids": [
                str(RESOURCE_ID_1),
            ],
            "prediction_at": "2026-11-08T12:00:00",
        },
    )

    assert response.status_code == 422


def test_ml_recommendation_service_unavailable():

    app = FastAPI()

    app.include_router(
        router,
        prefix="/api/v1/recommendations",
    )

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=USER_ID)
    )

    client = TestClient(app)

    response = client.post(
        "/api/v1/recommendations/ml",
        json={
            "resource_ids": [
                str(RESOURCE_ID_1),
            ]
        },
    )

    assert response.status_code == 503

    assert (
        response.json()["detail"]
        == "ML recommendation service is not configured."
    )


def test_ml_recommendation_uses_authenticated_user(
    client,
    service,
):
    client.post(
        "/api/v1/recommendations/ml",
        json={
            "resource_ids": [
                str(RESOURCE_ID_1),
            ]
        },
    )

    assert len(service.calls) == 1

    assert service.calls[0]["user_id"] == USER_ID