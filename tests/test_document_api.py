import uuid

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_current_user
from app.database.session import get_db

from app.services.document_database_service import (
    DocumentNotFoundError,
    list_user_documents,
    count_user_documents,
    get_user_document,
)


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
def client(user, mock_db):

    def override_current_user():
        return user

    def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = (
        override_current_user
    )

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_document_endpoints_require_authentication():

    with TestClient(app) as test_client:

        response = test_client.get(
            "/api/v1/documents"
        )

    assert response.status_code == 501


def test_list_documents(
    client,
    user,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.api.documents.list_user_documents",
        lambda **kwargs: [],
    )

    monkeypatch.setattr(
        "app.api.documents.count_user_documents",
        lambda **kwargs: 0,
    )

    response = client.get(
        "/api/v1/documents"
    )

    assert response.status_code == 200

    assert response.json() == {
        "items": [],
        "total": 0,
        "offset": 0,
        "limit": 20,
    }


def test_list_documents_uses_authenticated_user(
    client,
    user,
    monkeypatch,
):

    captured = {}

    def mock_list(**kwargs):

        captured.update(kwargs)

        return []

    monkeypatch.setattr(
        "app.api.documents.list_user_documents",
        mock_list,
    )

    monkeypatch.setattr(
        "app.api.documents.count_user_documents",
        lambda **kwargs: 0,
    )

    response = client.get(
        "/api/v1/documents"
    )

    assert response.status_code == 200

    assert captured["user_id"] == user.id


def test_document_not_found(
    client,
    user,
    monkeypatch,
):

    def mock_get(**kwargs):

        raise DocumentNotFoundError(
            "Document not found."
        )

    monkeypatch.setattr(
        "app.api.documents.get_user_document",
        mock_get,
    )

    response = client.get(
        f"/api/v1/documents/{uuid.uuid4()}"
    )

    assert response.status_code == 404


def test_invalid_document_uuid(client):

    response = client.get(
        "/api/v1/documents/not-a-uuid"
    )

    assert response.status_code == 422


def test_invalid_pagination(client):

    response = client.get(
        "/api/v1/documents?limit=500"
    )

    assert response.status_code == 422


def test_document_status_uses_owner_scoped_lookup(
    client,
    user,
    monkeypatch,
):

    document_id = uuid.uuid4()

    document = SimpleNamespace(
        id=document_id,
        processing_status="completed",
        processing_attempts=1,
        processing_started_at=None,
        processing_completed_at=None,
        processing_error=None,
        page_count=5,
    )

    captured = {}

    def mock_get(**kwargs):

        captured.update(kwargs)

        return document

    monkeypatch.setattr(
        "app.api.documents.get_user_document",
        mock_get,
    )

    response = client.get(
        f"/api/v1/documents/{document_id}/status"
    )

    assert response.status_code == 200

    assert response.json()["processing_status"] == "completed"

    assert captured["document_id"] == document_id

    assert captured["user_id"] == user.id