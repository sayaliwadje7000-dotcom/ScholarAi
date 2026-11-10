"""HTTP security headers, request correlation and API rate limiting."""

from __future__ import annotations

import json
import uuid
from typing import Any, Awaitable, Callable

from app.core.security_config import SecuritySettings, security_settings
from app.security.rate_limiter import InMemorySlidingWindowLimiter

ASGIApp = Callable[[dict[str, Any], Callable, Callable], Awaitable[None]]


class SecurityMiddleware:
    """Pure ASGI middleware; avoids buffering request/response bodies."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: SecuritySettings = security_settings,
        limiter: InMemorySlidingWindowLimiter | None = None,
    ):
        self.app = app
        self.settings = settings
        self.limiter = limiter or InMemorySlidingWindowLimiter(
            max_keys=settings.rate_limit_max_keys
        )

    @staticmethod
    def _client_ip(scope: dict[str, Any]) -> str:
        # Deliberately do not trust X-Forwarded-For here. Configure Uvicorn's
        # proxy_headers/forwarded_allow_ips or enforce limits at the trusted proxy.
        client = scope.get("client")
        if not client or not client[0]:
            return "unknown"
        return str(client[0])[:64]

    def _policies(self, path: str) -> list[tuple[str, int]]:
        window = self.settings.rate_limit_window_seconds
        policies = [("api", self.settings.api_requests_per_window)]
        auth_limits = {
            "/api/v1/auth/login": ("auth-login", self.settings.login_requests_per_window),
            "/api/v1/auth/register": ("auth-register", self.settings.registration_requests_per_window),
            "/api/v1/auth/refresh": ("auth-refresh", self.settings.refresh_requests_per_window),
        }
        if path in auth_limits:
            policies.append(auth_limits[path])
        return policies

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        request_id = str(uuid.uuid4())
        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        rate_headers: list[tuple[bytes, bytes]] = []
        if (
            self.settings.rate_limit_enabled
            and path.startswith("/api/v1/")
        ):
            ip = self._client_ip(scope)
            for bucket, limit in self._policies(path):
                decision = await self.limiter.check(
                    f"{ip}:{bucket}",
                    limit=limit,
                    window_seconds=self.settings.rate_limit_window_seconds,
                )
                rate_headers = [
                    (b"x-ratelimit-limit", str(decision.limit).encode("ascii")),
                    (b"x-ratelimit-remaining", str(decision.remaining).encode("ascii")),
                    (b"x-ratelimit-reset", str(decision.reset_after).encode("ascii")),
                ]
                if not decision.allowed:
                    body = json.dumps({
                        "detail": "Rate limit exceeded. Please try again later.",
                        "request_id": request_id,
                    }).encode("utf-8")
                    headers = [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"strict-origin-when-cross-origin"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                        (b"cross-origin-opener-policy", b"same-origin"),
                        (b"x-permitted-cross-domain-policies", b"none"),
                        (b"retry-after", str(decision.retry_after).encode("ascii")),
                        (b"x-request-id", request_id.encode("ascii")),
                        *rate_headers,
                    ]
                    if scope.get("scheme") == "https":
                        headers.append(
                            (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                        )
                    await send({
                        "type": "http.response.start",
                        "status": 429,
                        "headers": headers,
                    })
                    await send({
                        "type": "http.response.body",
                        "body": body,
                        "more_body": False,
                    })
                    return

        async def send_with_security_headers(message: dict[str, Any]):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {key.lower() for key, _ in headers}

                security_headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (b"cross-origin-opener-policy", b"same-origin"),
                    (b"x-permitted-cross-domain-policies", b"none"),
                    (b"x-request-id", request_id.encode("ascii")),
                ]
                if scope.get("scheme") == "https":
                    security_headers.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                if path.startswith("/api/v1/"):
                    security_headers.extend([
                        (b"cache-control", b"no-store"),
                        (b"pragma", b"no-cache"),
                    ])
                for key, value in security_headers:
                    if key not in existing:
                        headers.append((key, value))
                for key, value in rate_headers:
                    if key not in existing:
                        headers.append((key, value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
