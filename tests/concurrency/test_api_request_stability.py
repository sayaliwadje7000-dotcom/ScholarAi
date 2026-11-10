import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def stability_client():
    with TestClient(app) as client:
        yield client


def test_repeated_root_requests_remain_successful(stability_client):
    request_count = 50
    successful_requests = 0

    for _ in range(request_count):
        response = stability_client.get("/")

        assert response.status_code == 200

        successful_requests += 1

    assert successful_requests == request_count


def test_repeated_health_requests_remain_successful(stability_client):
    request_count = 30

    for _ in range(request_count):
        response = stability_client.get("/health")

        assert response.status_code == 200


def test_repeated_requests_have_non_negative_latency(stability_client):
    latencies = []

    for _ in range(20):
        started_at = time.perf_counter()

        response = stability_client.get("/")

        elapsed = time.perf_counter() - started_at

        assert response.status_code == 200

        latencies.append(elapsed)

    assert len(latencies) == 20
    assert all(latency >= 0 for latency in latencies)
