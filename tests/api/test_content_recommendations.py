from uuid import uuid4

import pytest

from fastapi.testclient import TestClient

from app.main import app

from app.api.dependencies import get_current_user

from app.api.content_recommendations import (
    get_content_recommendation_service,
)


class FakeUser:

    def __init__(self):
        self.id = uuid4()


class FakeRecommendationService:

    def recommend(self, db, user_id, request):

        return {
            "query": request.query,
            "total_results": 0,
            "recommendations": [],
            "algorithm_version": "content-based-v1",
            "status": "success",
        }


@pytest.fixture
def client():

    app.dependency_overrides[get_current_user] = (
        lambda: FakeUser()
    )

    app.dependency_overrides[
        get_content_recommendation_service
    ] = lambda: FakeRecommendationService()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_content_recommendation_endpoint(client):

    response = client.post(
        "/api/v1/recommendations/content-based",
        json={
            "query": "Learn Python programming",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["total_results"] == 0


def test_empty_query_rejected(client):

    response = client.post(
        "/api/v1/recommendations/content-based",
        json={
            "query": "",
        },
    )

    assert response.status_code == 422


def test_invalid_limit_rejected(client):

    response = client.post(
        "/api/v1/recommendations/content-based",
        json={
            "query": "Learn Python",
            "limit": 1000,
        },
    )

    assert response.status_code == 422


def test_unknown_fields_rejected(client):

    response = client.post(
        "/api/v1/recommendations/content-based",
        json={
            "query": "Learn Python",
            "unexpected": True,
        },
    )

    assert response.status_code == 422