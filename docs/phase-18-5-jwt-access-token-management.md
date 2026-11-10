# Phase 18.5 — JWT Access Token Management

## Objective

Implement signed JWT access tokens for authenticated
ScholarAI users.

## Security architecture

The authentication flow is:

1. User submits login credentials.
2. AuthService verifies the credentials.
3. Inactive users are rejected.
4. A JWT access token is generated.
5. The token is returned to the client.
6. The client sends the token in the Authorization header.
7. The authentication dependency validates the token.
8. The user is retrieved from PostgreSQL.
9. Inactive or deleted accounts are rejected.

## Token configuration

Configuration is provided through environment variables.

- SCHOLARAI_JWT_SECRET_KEY
- SCHOLARAI_JWT_ALGORITHM
- SCHOLARAI_JWT_ACCESS_TOKEN_EXPIRE_MINUTES
- SCHOLARAI_JWT_ISSUER
- SCHOLARAI_JWT_AUDIENCE

The default access-token lifetime is 15 minutes.

## JWT claims

| Claim | Purpose |
|---|---|
| sub | User UUID |
| jti | Unique token identifier |
| type | Access token type |
| iat | Issued-at timestamp |
| nbf | Not-before timestamp |
| exp | Expiration timestamp |
| iss | Token issuer |
| aud | Intended audience |

## Token security

The implementation:

- Uses an allowlisted signing algorithm.
- Requires a strong external signing secret.
- Verifies token signatures.
- Validates expiration.
- Validates issuer and audience.
- Validates required claims.
- Rejects malformed identity claims.
- Rejects non-access tokens.
- Rejects inactive users.
- Does not expose token values in logs.

## Authentication header

Protected endpoints require:

Authorization: Bearer <access_token>

## API behavior

Missing, invalid, malformed, expired, or
otherwise unacceptable tokens receive HTTP 401.

Database authentication failures receive HTTP 503.

## Deferred functionality

The following belong to Phase 18.6:

- Refresh tokens.
- Refresh-token rotation.
- Persistent sessions.
- Token-family tracking.
- Refresh-token revocation.
- Logout and session invalidation.

## Verification status

Implementation and test execution must be recorded
separately. This document does not imply that tests
have passed.