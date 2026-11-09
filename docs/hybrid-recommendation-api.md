# ScholarAI Hybrid Recommendation API

## 1. Purpose

This API exposes the hybrid recommendation engine
through the ScholarAI backend.

## 2. Intended Endpoint

Method:

POST

Path:

/api/v1/recommendations/hybrid

The route must be confirmed against the actual FastAPI
router registration before being treated as a deployed
API contract.

## 3. Request

The proposed request contract contains:

- query
- filters
- metadata
- limit

Example:

{
    "query": "Python data structures",
    "filters": {},
    "metadata": {},
    "limit": 10
}

## 4. Request Validation

The API must validate:

- Non-empty query.
- Valid filter structure.
- Valid metadata structure.
- Positive recommendation limit.
- Maximum recommendation limit.

## 5. User Context

The endpoint must derive user identity from a trusted
authentication context.

The user must not be allowed to impersonate another
user by submitting an arbitrary user identifier.

Authentication enforcement must be verified separately
against the application's current security implementation.

## 6. Response

The response should expose:

- Request identifier.
- Recommendation items.
- Resource identifiers.
- Resource titles.
- Resource types.
- Hybrid scores.
- Ranking positions.
- Explanations.
- Component execution reports.
- Fallback information.
- Diagnostic warnings where appropriate.

## 7. Error Handling

Expected error categories include:

400:
Invalid request or business-level input.

422:
Request schema validation failure.

503:
Recommendation service unavailable.

500:
Unexpected internal failure.

Internal stack traces and secrets must never be returned
to clients.

## 8. Dependency Injection

The hybrid orchestrator should be provided through
application dependency injection or an application
composition root.

The API router must not create a new recommendation
engine for every request.

## 9. Backward Compatibility

Existing recommendation endpoints must continue to work.

The hybrid endpoint must not silently change the response
contracts of existing recommendation APIs.

## 10. Verification Checklist

- Router imported.
- Router registered.
- Dependency resolves the orchestrator.
- Request validation works.
- Response serialization works.
- User identity is trusted.
- Failure responses are structured.
- Existing recommendation endpoints remain functional.