# Phase 18.9 — Authorization and Resource Ownership

## Objective

Ensure authenticated users can access or mutate only private resources that belong to them. Resource ownership is derived from the authenticated database user, never from a request body, query parameter, or client-controlled request state.

## Existing controls retained

- Document upload assigns `Document.user_id` from `get_current_user`.
- Document listing, metadata, and status queries use both document ID and authenticated user ID.
- Semantic retrieval resolves requested document IDs through `Document.user_id` before passing IDs to vector search.
- RAG forwards the authenticated user ID to retrieval.
- Recommendation history is filtered by `Recommendation.user_id`.
- Recommendation feedback first resolves the recommendation using both recommendation ID and owner ID.
- Learning profile, learning goals, personalization controls, and behavioral signal reads are scoped by the authenticated user ID.
- ML and content-based recommendation services receive the authenticated user ID.

## Phase 18.9 changes

1. Hybrid recommendation API now depends on `get_current_user`; it no longer trusts `request.state.user_id`.
2. Hybrid orchestration receives `current_user.id` and the response verifies the orchestrator retained that identity.
3. Learning activity creation validates ownership when an activity references a private `document` or `recommendation`. Missing and foreign-owned references produce the same not-found result.
4. Recommendation feedback locks the owner-scoped recommendation row during submission. A concurrent duplicate is translated to HTTP 409 through the database uniqueness constraint.
5. Duplicate authentication router registration in `app/main.py` is removed.

## Ownership rules

- Private resource lookups must include the authenticated owner in the database predicate.
- Child resources inherit ownership through their parent. Document chunks are retrieved only after their parent document IDs have been verified.
- Shared catalog resources are not treated as user-owned records.
- Internal background processing may load a document by ID only when invoked from a trusted server-side workflow created after an owner-scoped upload; it is not an end-user lookup API.
- Do not return whether a foreign-owned private resource exists. Return the same HTTP 404 response as for a nonexistent resource.

## Deferred / separate concerns

- Persistent session-ID validation in `get_current_user` belongs to the Phase 18.6 session integration follow-up; it is not silently represented as complete by this phase.
- Database row-level security is not enabled. Application-level owner-scoped predicates remain mandatory.
- The generic `LearningActivity.entity_id` intentionally has no polymorphic foreign key. This phase validates the private entity types currently recognized by the service (`document` and `recommendation`). New private entity types must add equivalent ownership checks before being accepted.

## Verification

Run focused tests:

```powershell
python -m pytest tests/api/test_hybrid_recommendations.py tests/api/test_hybrid_recommendation_api_contract.py tests/auth/test_resource_ownership.py tests/test_retrieval_api.py tests/test_rag_api.py -q
```

Then run the complete regression suite:

```powershell
python -m pytest -v
```

Do not mark the phase verified until both commands complete successfully against the current environment and database configuration.
