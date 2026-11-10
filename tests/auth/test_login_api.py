import uuid

from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app

from app.database.session import get_db

from app.services.auth_service import (
    auth_service,
)

from app.services.auth_exceptions import (
    AuthenticationError,
)
from app.core.jwt_config import jwt_settings

def create_mock_user():

    user = MagicMock()

    user.id = uuid.uuid4()

    user.full_name = "ScholarAI Student"

    user.email = "student@example.com"

    user.is_active = True

    user.created_at = datetime.now(timezone.utc)

    return user


def test_login_api_success(monkeypatch):

    db = MagicMock()

    app.dependency_overrides[get_db] = lambda: db

    user = create_mock_user()

    monkeypatch.setattr(
        auth_service,
        "authenticate_user",
        lambda db, request: user,
    )

    try:

        with TestClient(app) as client:

            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "student@example.com",
                    "password": "SecurePassword123!",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["authenticated"] is True

        assert (
            body["user"]["email"]
            == "student@example.com"
        )

        assert "password_hash" not in body

        assert "password" not in body

        assert "access_token" in body

        assert isinstance(body["access_token"], str)
        assert len(body["access_token"]) > 0

        assert body["token_type"] == "bearer"

        assert body["expires_in"] == (
    jwt_settings.access_token_expire_minutes * 60
)

    finally:

        app.dependency_overrides.clear()


def test_login_api_invalid_credentials(monkeypatch):

    db = MagicMock()

    app.dependency_overrides[get_db] = lambda: db

    def reject_credentials(db, request):

        raise AuthenticationError()

    monkeypatch.setattr(
        auth_service,
        "authenticate_user",
        reject_credentials,
    )

    try:

        with TestClient(app) as client:

            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "student@example.com",
                    "password": "WrongPassword123!",
                },
            )

        assert response.status_code == 401

        assert response.json()["detail"] == (
            "Invalid email or password."
        )

    finally:

        app.dependency_overrides.clear()


def test_login_api_invalid_payload():

    with TestClient(app) as client:

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "invalid-email",
                "password": "SecurePassword123!",
            },
        )

    assert response.status_code == 422