# ScholarAI — Phase 10.9: Recommendation API Integration

## Objective

Integrate the rule-based recommendation engine with the FastAPI
application and PostgreSQL persistence layer.

## Endpoints

### 1. Generate Recommendations

POST /api/v1/recommendations/generate

Accepts RecommendationRequest.

Workflow:

1. Resolve authenticated user.
2. Load user preferences.
3. Retrieve recent resource interactions.
4. Retrieve active educational resources.
5. Classify resource metadata.
6. Build learning context.
7. Evaluate recommendation scores.
8. Apply eligibility and filtering.
9. Rank candidates.
10. Generate recommendation explanations.
11. Persist recommendation records.
12. Return structured results.

### 2. Retrieve Recommendations

GET /api/v1/recommendations/

Query parameters:

- limit
- offset

Returns recommendations belonging exclusively to the
authenticated user.

### 3. Submit Feedback

POST /api/v1/recommendations/{recommendation_id}/feedback

Supported feedback:

- helpful
- not_helpful
- irrelevant

Only the owner of the recommendation can submit feedback.

One feedback record is permitted per recommendation,
consistent with the database uniqueness constraint.

## Persistence

Uses existing tables:

- study_resources
- user_resource_interactions
- recommendations
- recommendation_feedback
- users
- user_preferences

No additional database tables are required.

## Security

All recommendation endpoints depend on get_current_user.

Authentication currently returns HTTP 501 and remains
deferred until Phase 18.

Tests may override the dependency with a controlled
test user.

## Reliability

- User-scoped queries.
- Transactional recommendation persistence.
- Database rollback on failure.
- Pydantic request validation.
- Bounded pagination.
- Duplicate feedback protection.
- No exposure of internal exception details.

## Future Work

Phase 10.10 completes recommendation evaluation,
integration testing and documentation.

Authentication implementation remains in Phase 18.