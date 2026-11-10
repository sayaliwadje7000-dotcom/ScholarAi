# Phase 18.11 — Security Testing

## Objective

Verify the authentication, session validation, role authorization, ownership boundaries, rate limiting, and HTTP security controls delivered in Phases 18.2–18.10. This phase adds adversarial and regression tests; it does not replace production security controls.

## Test coverage

| Area | Test module | Security property |
|---|---|---|
| JWT claims | `tests/security/test_jwt_claim_validation.py` | Rejects wrong issuer/audience, missing claims, malformed session IDs; accepts correctly signed session-bound tokens |
| RBAC | `tests/security/test_rbac_authorization_matrix.py` | Student, educator, admin, denied, and no-role authorization matrix |
| Rate limiter | `tests/security/test_rate_limiter_adversarial.py` | Concurrent limit enforcement, invalid input rejection, bounded key storage, window boundary |
| Middleware | `tests/security/test_security_middleware_hardening.py` | Security headers, request IDs, endpoint-specific limits, health exemption, disabled mode |
| Configuration | `tests/security/test_security_configuration.py` | Environment parsing and invalid-value rejection |
| Authentication/session | Existing `tests/auth/test_authentication_dependency.py` | Missing/invalid token, session-bound token, missing/revoked/expired session behavior, inactive user and DB failure |
| Ownership | Existing `tests/auth/test_resource_ownership.py` and Phase 18.9 API tests | Cross-user access prevention for owned resources |
| Route authorization | Existing `tests/auth/test_route_protection.py` | Student/admin access and denial for other/no roles |
| Password and refresh | Existing `tests/auth/test_password_hashing.py`, `test_password_policy.py`, `test_refresh_sessions.py` | Password storage and session lifecycle regression |

## Run focused security tests

From the repository root, with the project virtual environment active:

```powershell
python -m pytest tests/auth tests/security tests/api/test_hybrid_recommendations.py tests/api/test_hybrid_recommendation_api_contract.py -v
```

Run the complete regression suite afterward:

```powershell
python -m pytest -v
```

## Required manual checks

1. Register a normal user and confirm the stored password is an Argon2 hash, never plaintext.
2. Log in and confirm the access token includes a session ID (`sid`) and the refresh token is returned only over HTTPS in production.
3. Revoke the session; verify the previously issued access token receives HTTP 401 on its next request.
4. Expire a session; verify the access token receives HTTP 401.
5. Verify a student cannot access admin-only role-management endpoints (HTTP 403).
6. Verify one user cannot read, modify, or submit feedback against another user's private resource.
7. Exceed login and general API limits; verify HTTP 429 and `Retry-After`.
8. Confirm health checks remain available when API rate limits are exhausted.
9. Confirm security headers and request IDs appear on normal and rate-limited responses.

## Operational caveats

- The Phase 18.10 limiter is in-memory and process-local. It does not provide a global limit across multiple workers, containers, or replicas. Use a shared Redis limiter or trusted API gateway before horizontal scaling.
- IP-based limiting must not trust arbitrary `X-Forwarded-For` values. Configure trusted proxy handling explicitly at deployment.
- HSTS should be enabled only when the service is served exclusively over HTTPS and all included subdomains support HTTPS.
- Automated unit tests do not constitute a penetration test, external vulnerability assessment, or production security certification.
- Never commit `.env`, JWT secrets, API keys, passwords, access tokens, refresh tokens, or real user data.

## Completion criteria

Phase 18.11 is complete only when focused security tests and the full regression suite pass in the project's actual `.venv`, manual checks are recorded, and all failures are resolved or documented as accepted risks. Record actual test counts and skipped tests; do not infer success from syntax compilation.

## Status

Implementation supplied. Test execution and manual security checks are pending user verification.
