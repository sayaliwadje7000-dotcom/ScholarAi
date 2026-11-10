# Phase 18.4 — Login and Credential Verification

## Objective

Implement the ScholarAI login and credential verification workflow.

## Implemented Components

1. Login request schema.
2. Login response schema.
3. Email normalization.
4. Email-based user lookup.
5. Password verification.
6. Generic authentication errors.
7. Inactive account rejection.
8. Legacy account handling.
9. Automatic Argon2id hash upgrade support.
10. Database persistence of upgraded hashes.
11. Login API endpoint.
12. Login schema tests.
13. Login service tests.
14. Login API tests.

## Endpoint

POST /api/v1/auth/login

## Request

{
    "email": "student@example.com",
    "password": "SecurePassword123!"
}

## Successful Response

HTTP 200 OK

{
    "authenticated": true,
    "message": "Credentials verified successfully.",
    "user": {
        "id": "generated-user-uuid",
        "full_name": "ScholarAI Student",
        "email": "student@example.com",
        "is_active": true,
        "created_at": "timestamp"
    }
}

## Failed Authentication

HTTP 401 Unauthorized

{
    "detail": "Invalid email or password."
}

The same generic authentication response is used for
unknown accounts, incorrect passwords, and inactive accounts.

## Password Hash Upgrade

Successful verification checks whether the stored
Argon2id hash needs upgrading.

If required, the password hash is regenerated and
persisted using the current configuration.

## Database Changes

No new database migration is required.

The password_hash column was introduced in Phase 18.2.

## Security Boundaries

- Plaintext passwords are never persisted.
- Password hashes are never returned by the API.
- Generic authentication errors prevent account enumeration.
- Inactive accounts cannot authenticate.
- Password verification does not apply registration
  password policy to existing credentials.
- Hash upgrades occur only after successful verification.

## Deferred Work

- JWT access token issuance: Phase 18.5.
- Refresh-token sessions: Phase 18.6.
- Role-based authorization: Phase 18.7.
- Protected route integration: Phase 18.8.
- Login rate limiting: Phase 18.10.

## Completion Criteria

- Login schema validation.
- Email-based account lookup.
- Correct password verification.
- Incorrect password rejection.
- Inactive account rejection.
- Missing password hash handling.
- Password hash upgrade.
- Login API integration.
- Automated test verification.