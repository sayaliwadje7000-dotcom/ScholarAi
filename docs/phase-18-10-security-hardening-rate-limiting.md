# Phase 18.10 — Security Hardening and Rate Limiting

## Objective

Harden the existing FastAPI security boundary without replacing the Phase 18.2–18.9 architecture. This implementation adds session-bound access-token enforcement, API rate limiting, security response headers, request correlation, and CORS method alignment.

## Delivered components

### 1. Persistent-session validation for access tokens

`app/api/dependencies.py` now requires the access token to contain a valid UUID `sid` claim. After resolving an active user, `get_current_user` verifies that the matching `UserSession`:

- belongs to the authenticated user;
- has not been revoked; and
- has not expired.

A missing, revoked, expired, or mismatched session is rejected with the same generic `401` response. Database failures return `503`, rather than being mistaken for invalid credentials. This closes the previously identified gap between Phase 18.5 token validation and Phase 18.6 persistent sessions.

Access tokens minted without a session ID remain decodable for low-level token tests and migration diagnostics, but they cannot authenticate API requests. Production issuance already occurs through `SessionService`, which supplies `session_id`.

### 2. Rate limiting

`app/security/rate_limiter.py` implements a bounded asynchronous sliding-window limiter. Defaults per client IP and 60-second window:

| Route category | Limit |
| --- | ---: |
| General `/api/v1/*` API | 120 requests |
| `POST /api/v1/auth/login` | 5 requests |
| `POST /api/v1/auth/register` | 5 requests |
| `POST /api/v1/auth/refresh` | 10 requests |

Authentication endpoints are subject to both their endpoint-specific policy and the general API policy. Rejected requests receive HTTP `429`, `Retry-After`, rate-limit headers, and a request ID. Health endpoints are excluded.

**Deployment limitation:** this limiter is process-local. Its counters are not shared across Uvicorn workers, containers, or machines. For a multi-worker or horizontally scaled production deployment, enforce equivalent limits at a trusted API gateway/load balancer or replace the in-process store with a shared Redis-backed implementation. Do not treat this local limiter as a distributed abuse-control system.

The middleware deliberately does not trust a client-supplied `X-Forwarded-For` header. If ScholarAI runs behind a reverse proxy, configure Uvicorn's trusted proxy settings and enforce edge rate limits at that proxy. Do not trust arbitrary forwarded headers from the public internet.

### 3. Security headers and request correlation

`app/security/security_middleware.py` adds:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- a restrictive `Permissions-Policy`
- `Cross-Origin-Opener-Policy: same-origin`
- `X-Permitted-Cross-Domain-Policies: none`
- `X-Request-ID` generated server-side for every HTTP request
- `Cache-Control: no-store` and `Pragma: no-cache` on API responses
- HSTS only when the ASGI request scheme is HTTPS

The request ID is also placed in `scope['state']['request_id']` for downstream logging/instrumentation.

### 4. Configuration

`app/core/security_config.py` reads and validates:

| Environment variable | Default | Purpose |
| --- | ---: | --- |
| `SCHOLARAI_RATE_LIMIT_ENABLED` | `true` | Enable/disable app-level limiter |
| `SCHOLARAI_RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding-window duration |
| `SCHOLARAI_API_RATE_LIMIT` | `120` | General API limit |
| `SCHOLARAI_LOGIN_RATE_LIMIT` | `5` | Login limit |
| `SCHOLARAI_REGISTER_RATE_LIMIT` | `5` | Registration limit |
| `SCHOLARAI_REFRESH_RATE_LIMIT` | `10` | Refresh limit |
| `SCHOLARAI_RATE_LIMIT_MAX_KEYS` | `50000` | Bound in-memory client buckets |

Invalid, zero, negative, or excessive values fail configuration loading rather than silently weakening the controls.

### 5. CORS and application integration

- Security middleware is registered in `app/main.py`.
- CORS methods include `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, and `HEAD`, matching the API's method surface.
- Authentication router registration is deduplicated so `/api/v1/auth` is mounted once.
- Existing Phase 18.8 role dependencies and Phase 18.9 ownership controls are retained.

## Tests added/updated

- `tests/auth/test_authentication_dependency.py`: session-bound token acceptance, sid-less token rejection, invalid session rejection, inactive user rejection, and database failure handling.
- `tests/security/test_rate_limiter.py`: sliding-window limits, retry delay, expiration, and key isolation.
- `tests/security/test_security_middleware.py`: response headers, request ID, auth endpoint throttling, and health-route exemption.

## Verification commands

Run from the project root with `.venv` activated:

```powershell
python -m pytest tests/auth/test_authentication_dependency.py tests/security -v
python -m pytest -v
```

Also verify route registration and configuration:

```powershell
python -c "from app.main import app; paths=[r.path for r in app.routes]; print('auth login registrations:', paths.count('/api/v1/auth/login')); print('route count:', len(paths))"
python -m compileall -q app tests/security
```

Expected auth login registration count: `1`.

## Operational security checklist

1. Keep `SCHOLARAI_JWT_SECRET_KEY` secret, random, and at least 32 bytes; never commit it.
2. Use HTTPS in production; terminate TLS at a trusted ingress and ensure the ASGI scheme is correctly forwarded only by trusted proxies.
3. Configure trusted proxy IPs explicitly; never trust arbitrary `X-Forwarded-For` values.
4. Use a shared gateway or Redis-backed limiter when deploying multiple workers/instances.
5. Keep document upload size/page limits enabled; this middleware does not replace file-content validation.
6. Monitor `401`, `403`, `429`, and `5xx` rates. Correlate application logs using `X-Request-ID`.
7. Keep API documentation endpoints disabled or access-restricted in production if they are not intended to be public.

## Status

Implementation is supplied. Tests must be run in the project's Windows `.venv` and the full regression suite must pass before this phase is marked verified or committed. No database migration is required.
