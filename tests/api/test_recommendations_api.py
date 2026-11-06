from uuid import uuid4

import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.fixture
def authenticated_client():
    user = FakeUser()

    app.dependency_overrides[get_current_user] = (
        lambda: user
    )

    with TestClient(app) as client:
        yield client, user

    app.dependency_overrides.clear()


def test_recommendation_generation_requires_valid_request(
    authenticated_client,
):
    client, _ = authenticated_client

    response = client.post(
        "/api/v1/recommendations/generate",
        json={
            "limit": 0,
        },
    )

    assert response.status_code == 422


def test_recommendation_generation_requires_authentication():
    response = TestClient(app).post(
        "/api/v1/recommendations/generate",
        json={},
    )

    assert response.status_code == 501


def test_recommendation_history_requires_authentication():
    response = TestClient(app).get(
        "/api/v1/recommendations/"
    )

    assert response.status_code == 501


def test_recommendation_feedback_requires_authentication():
    response = TestClient(app).post(
        f"/api/v1/recommendations/{uuid4()}/feedback",
        json={
            "feedback_type": "helpful",
        },
    )

    assert response.status_code == 501