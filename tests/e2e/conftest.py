import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def e2e_client():
    original_overrides = app.dependency_overrides.copy()

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
