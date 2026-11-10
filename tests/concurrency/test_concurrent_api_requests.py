from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def concurrent_client():
    with TestClient(app) as client:
        yield client


def send_root_request(client):
    response = client.get("/")

    return {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "body": response.json(),
    }


def test_application_handles_concurrent_root_requests(concurrent_client):
    request_count = 24
    worker_count = 8

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(
            executor.map(
                lambda _: send_root_request(concurrent_client),
                range(request_count),
            )
        )

    assert len(results) == request_count

    for result in results:
        assert result["status_code"] == 200
        assert result["content_type"].startswith("application/json")
        assert isinstance(result["body"], dict)


def test_application_handles_concurrent_health_requests(concurrent_client):
    request_count = 16
    worker_count = 8

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        responses = list(
            executor.map(
                lambda _: concurrent_client.get("/health"),
                range(request_count),
            )
        )

    assert len(responses) == request_count

    for response in responses:
        assert response.status_code == 200
