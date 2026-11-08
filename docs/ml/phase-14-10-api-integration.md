# Phase 14.10 — ML Recommendation API Integration

## Objective

Expose the Phase 14.9 machine-learning recommendation service
through a versioned FastAPI endpoint.

## Endpoint

POST /api/v1/recommendations/ml

## Authentication

The endpoint depends on the existing get_current_user dependency.

Authentication is not implemented in Phase 14.10.
The current dependency returns HTTP 501 until Phase 18.

Tests override the dependency with a controlled test user.
The endpoint must not accept an arbitrary user_id from the request.

## Request

{
  "resource_ids": [
    "resource-uuid"
  ],
  "prediction_at": "2026-11-08T12:00:00Z"
}

prediction_at is optional and defaults to UTC now.

## Response

The response contains:

- Authenticated user ID
- Model run ID
- Total prediction count
- Resource IDs
- Relevance probabilities
- Relevance decisions
- Generation timestamp

## Architecture

HTTP request
    |
    v
FastAPI route
    |
    v
Authenticated user dependency
    |
    v
ML service dependency
    |
    v
Phase 14.9 RecommendationMLService
    |
    v
Structured API response

## Error handling

- 422: invalid request
- 501: authentication not implemented
- 503: ML service unavailable or inference failure
- 500: response serialization failure

## Boundaries

This phase does not:

- Train models during API requests.
- Accept user IDs supplied by clients.
- Load arbitrary model files from request data.
- Replace rule-based or content-based recommendations.
- Implement Phase 15 hybrid orchestration.
- Implement Phase 18 authentication.

## Verification

The API tests use an injected fake ML service.

A separate integration test must verify the actual
Phase 14.9 service, fitted transformer and model bundle.