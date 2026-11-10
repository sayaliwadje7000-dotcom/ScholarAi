"""Phase 18.11: middleware security contract and endpoint policy tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security_config import SecuritySettings
from app.security.rate_limiter import InMemorySlidingWindowLimiter
from app.security.security_middleware import SecurityMiddleware


def _client(*, api_limit=20, login_limit=2):
    app = FastAPI()

    @app.get("/api/v1/probe")
    def probe():
        return {"ok": True}

    @app.post("/api/v1/auth/login")
    def login():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    config = SecuritySettings(
        rate_limit_enabled=True,
        rate_limit_window_seconds=60,
        api_requests_per_window=api_limit,
        login_requests_per_window=login_limit,
        registration_requests_per_window=2,
        refresh_requests_per_window=2,
        rate_limit_max_keys=100,
    )
    app.add_middleware(
        SecurityMiddleware,
        settings=config,
        limiter=InMemorySlidingWindowLimiter(max_keys=100),
    )
    return TestClient(app)


def test_security_headers_are_present_and_request_id_is_unique():
    client = _client()
    first = client.get("/api/v1/probe")
    second = client.get("/api/v1/probe")
    for response in (first, second):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"]
        assert response.headers["permissions-policy"]
        assert response.headers["cache-control"] == "no-store"
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_auth_endpoint_has_stricter_limit_than_general_api():
    client = _client(api_limit=20, login_limit=2)
    assert client.post("/api/v1/auth/login").status_code == 200
    assert client.post("/api/v1/auth/login").status_code == 200
    blocked = client.post("/api/v1/auth/login")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1
    assert blocked.headers["x-request-id"]


def test_health_route_is_not_rate_limited():
    client = _client(api_limit=1, login_limit=1)
    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_general_api_limit_is_enforced():
    client = _client(api_limit=1, login_limit=2)
    assert client.get("/api/v1/probe").status_code == 200
    assert client.get("/api/v1/probe").status_code == 429


def test_rate_limit_disabled_allows_requests():
    app = FastAPI()

    @app.get("/api/v1/probe")
    def probe():
        return {"ok": True}

    config = SecuritySettings(rate_limit_enabled=False)
    app.add_middleware(SecurityMiddleware, settings=config)
    client = TestClient(app)
    for _ in range(5):
        assert client.get("/api/v1/probe").status_code == 200
