import os
import secrets
import uuid
from types import SimpleNamespace

os.environ.setdefault("SCHOLARAI_JWT_SECRET_KEY", secrets.token_urlsafe(48))

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.security.permissions import require_student_or_admin
from app.services.role_service import role_service


def build_client(monkeypatch, roles):
    app = FastAPI()
    user = SimpleNamespace(id=uuid.uuid4())

    def fake_current_user():
        return user

    def fake_db():
        return object()

    monkeypatch.setattr(
        role_service,
        "get_user_roles",
        lambda db, user_id: set(roles),
    )

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = fake_db

    @app.get("/protected")
    def protected_route(_user=Depends(require_student_or_admin)):
        return {"allowed": True}

    return TestClient(app)


def test_student_can_access_student_route(monkeypatch):
    client = build_client(monkeypatch, {"student"})
    response = client.get("/protected")
    assert response.status_code == 200
    assert response.json() == {"allowed": True}


def test_admin_can_access_student_route(monkeypatch):
    client = build_client(monkeypatch, {"admin"})
    response = client.get("/protected")
    assert response.status_code == 200


def test_educator_without_student_role_is_denied(monkeypatch):
    client = build_client(monkeypatch, {"educator"})
    response = client.get("/protected")
    assert response.status_code == 403


def test_user_without_roles_is_denied(monkeypatch):
    client = build_client(monkeypatch, set())
    response = client.get("/protected")
    assert response.status_code == 403
