from concurrent.futures import ThreadPoolExecutor, as_completed
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def load_test_client():
    with TestClient(app) as client:
        yield client


def test_application_handles_bounded_concurrent_load(load_test_client):
    worker_count = 5
    requests_per_worker = 10
    total_requests = worker_count * requests_per_worker

    started_at = time.perf_counter()

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(load_test_client.get, "/")
            for _ in range(total_requests)
        ]

        responses = [
            future.result()
            for future in as_completed(futures)
        ]

    elapsed = time.perf_counter() - started_at

    assert len(responses) == total_requests

    for response in responses:
        assert response.status_code == 200

    assert elapsed >= 0


def test_application_handles_concurrent_health_load(load_test_client):
    worker_count = 5
    total_requests = 25

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(load_test_client.get, "/health")
            for _ in range(total_requests)
        ]

        responses = [
            future.result()
            for future in as_completed(futures)
        ]

    assert len(responses) == total_requests

    for response in responses:
        assert response.status_code == 200
