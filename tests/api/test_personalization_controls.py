import uuid

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.personalization_controls import router
from app.database.session import get_db
from app.models.user import User
from app.models.user_preferences import UserPreferences


class FakeSession:
    """In-memory session for personalization API tests."""

    def __init__(self):
        self.preferences = {}
        self.committed = False
        self.rolled_back = False

    def scalar(self, statement):
        where_clause = statement.whereclause
        user_id = where_clause.right.value

        return self.preferences.get(user_id)

    def add(self, instance):
        if isinstance(instance, UserPreferences):
            self.preferences[instance.user_id] = instance

    def flush(self):
        pass

    def commit(self):
        self.committed = True

    def refresh(self, instance):
        pass

    def rollback(self):
        self.rolled_back = True


@pytest.fixture
def api_client():

    db = FakeSession()

    user = User(
        id=uuid.uuid4(),
        full_name="API Test Student",
        email=f"{uuid.uuid4()}@example.com",
        is_active=True,
    )

    app = FastAPI()

    app.include_router(
        router,
        prefix="/api/v1/personalization-controls",
    )

    def override_get_db():
        yield db

    def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    with TestClient(app) as client:
        yield client


def test_get_personalization_controls(api_client):

    response = api_client.get(
        "/api/v1/personalization-controls/"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["preferred_language"] is None
    assert data["education_level"] is None
    assert data["preferred_subjects"] == []
    assert data["notification_enabled"] is True


def test_update_personalization_controls(api_client):

    response = api_client.patch(
        "/api/v1/personalization-controls/",
        json={
            "preferred_language": "English",
            "education_level": "Undergraduate",
            "preferred_subjects": [
                "Data Structures",
            ],
            "notification_enabled": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["preferred_language"] == "English"
    assert data["education_level"] == "Undergraduate"

    assert data["preferred_subjects"] == [
        "Data Structures",
    ]

    assert data["notification_enabled"] is False


def test_partial_update(api_client):

    api_client.patch(
        "/api/v1/personalization-controls/",
        json={
            "preferred_language": "English",
            "notification_enabled": True,
        },
    )

    response = api_client.patch(
        "/api/v1/personalization-controls/",
        json={
            "preferred_language": "Marathi",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["preferred_language"] == "Marathi"
    assert data["notification_enabled"] is True


def test_reset_personalization_controls(api_client):

    api_client.patch(
        "/api/v1/personalization-controls/",
        json={
            "preferred_language": "English",
            "preferred_subjects": [
                "Mathematics",
            ],
            "notification_enabled": False,
        },
    )

    response = api_client.post(
        "/api/v1/personalization-controls/reset"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["controls"]["preferred_language"] is None
    assert data["controls"]["education_level"] is None
    assert data["controls"]["preferred_subjects"] == []
    assert data["controls"]["notification_enabled"] is True


def test_empty_update_is_rejected(api_client):

    response = api_client.patch(
        "/api/v1/personalization-controls/",
        json={},
    )

    assert response.status_code == 400


def test_invalid_subject_is_rejected(api_client):

    response = api_client.patch(
        "/api/v1/personalization-controls/",
        json={
            "preferred_subjects": [
                "Data Structures",
                " ",
            ]
        },
    )

    assert response.status_code == 422