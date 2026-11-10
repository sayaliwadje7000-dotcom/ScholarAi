# ScholarAI Phase 18.8 â€” API Route Protection

## Objective
Apply database-backed role authorization to student-facing API routers while preserving existing authentication and ownership checks.

## Policy
- Student role: allowed to access student-facing routes.
- Administrator role: allowed to access student-facing routes for operational administration.
- Educator role alone: not implicitly treated as student. Educators requiring student-facing functionality must also have the student role.
- Administrative role-management endpoints remain governed by `require_admin`.
- Authentication registration/login and health endpoints are not placed behind student-role checks.

## Protected routers
- Chat
- Documents
- Retrieval
- RAG
- Recommendations
- Content recommendations
- Educational resource recommendations
- Opportunities
- ML recommendations
- Hybrid recommendations
- Learning profile
- Learning activities
- Personalization controls

The policy is applied at `app.include_router(...)` registration in `app/main.py`, so every endpoint in each listed router inherits the role check. Existing endpoint-level `get_current_user` dependencies and resource ownership checks are retained.

## Important boundary
Role authorization is not a replacement for resource ownership. Each document, learning activity, profile, recommendation, or personalization record must still be scoped to the authenticated user's ID. Cross-user ownership enforcement is reviewed separately in Phase 18.9.

## Tests
Run:
```powershell
python -m pytest tests/auth/test_route_protection.py -v
python -m pytest tests/auth/ -v
python -m pytest -v
```

The route dependency tests verify student/admin access and denial for educator-only or role-less users. Full API integration tests must additionally verify unauthenticated requests, role denial, and ownership isolation.

## Status
Implementation generated. Do not mark Phase 18.8 complete until imports, route registration, targeted tests, authentication tests, full regression tests, and Swagger authorization checks pass.
