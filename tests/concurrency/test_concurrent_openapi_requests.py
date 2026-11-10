from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def openapi_client():
    with TestClient(app) as client:
        yield client


def test_openapi_supports_concurrent_requests(openapi_client):
    request_count = 20
    worker_count = 8

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        responses = list(
            executor.map(
                lambda _: openapi_client.get("/openapi.json"),
                range(request_count),
            )
        )

    assert len(responses) == request_count

    for response in responses:
        assert response.status_code == 200

        schema = response.json()

        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema


def test_concurrent_openapi_requests_return_consistent_schema(
    openapi_client,
):
    with ThreadPoolExecutor(max_workers=6) as executor:
        schemas = list(
            executor.map(
                lambda _: openapi_client.get("/openapi.json").json(),
                range(12),
            )
        )

    reference_paths = set(schemas[0]["paths"].keys())

    for schema in schemas:
        assert set(schema["paths"].keys()) == reference_paths
