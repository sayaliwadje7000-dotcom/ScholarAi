from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security_config import SecuritySettings
from app.security.rate_limiter import InMemorySlidingWindowLimiter
from app.security.security_middleware import SecurityMiddleware


def build_client():
    app = FastAPI()

    @app.get("/api/v1/probe")
    def probe():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    settings = SecuritySettings(
        rate_limit_enabled=True,
        rate_limit_window_seconds=60,
        api_requests_per_window=10,
        login_requests_per_window=2,
        registration_requests_per_window=2,
        refresh_requests_per_window=2,
        rate_limit_max_keys=100,
    )
    limiter = InMemorySlidingWindowLimiter(max_keys=100)
    app.add_middleware(SecurityMiddleware, settings=settings, limiter=limiter)
    return TestClient(app)


def test_security_headers_and_request_id_are_added():
    client = build_client()
    response = client.get("/api/v1/probe")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_authentication_endpoint_is_rate_limited():
    client = build_client()
    for _ in range(2):
        response = client.post("/api/v1/auth/login")
        # The test route does not exist; 404 still consumes the configured bucket.
        assert response.status_code == 404
    blocked = client.post("/api/v1/auth/login")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1
    assert blocked.json()["request_id"]


def test_health_endpoint_is_not_rate_limited():
    client = build_client()
    for _ in range(3):
        assert client.get("/health").status_code == 200
