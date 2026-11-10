# Phase 18.6 — Refresh Token and Session Management

## Implemented components

- Persistent user sessions using the user_sessions table.
- Cryptographically signed refresh JWTs.
- SHA-256 refresh-token hashing.
- Constant-time hash comparison.
- Refresh-token rotation.
- Refresh-token reuse detection.
- Session revocation.
- Logout support at the service layer.
- Revoke-all-sessions support.
- Session listing support.
- Database row locking during refresh rotation.

## Security properties

1. Refresh tokens are signed using the existing JWT secret.
2. Refresh tokens have a distinct type claim.
3. Refresh tokens are bound to a user and session.
4. Raw refresh tokens are not stored in the database.
5. Old refresh-token reuse revokes the associated session.
6. Expired and revoked sessions cannot be refreshed.
7. Refresh rotation uses SELECT FOR UPDATE.
8. Session expiration is absolute and is not extended by rotation.

## Integration requirements

- Login must create a persistent session.
- Access tokens must contain a session identifier (sid).
- Protected requests must reject revoked or expired sessions.
- Refresh endpoint must call SessionService.rotate_refresh_token.
- Logout endpoint must revoke the authenticated session.
- Session listing and revocation endpoints must enforce ownership.

## Verification

Run:

    python -m pytest tests/auth/test_refresh_sessions.py -v

Run the full test suite after API integration:

    python -m pytest -v

Do not mark the phase complete until all integration tests pass.
