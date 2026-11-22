# Phase 21.1 — Architecture Acceptance Checklist

## Objective

Verify that the ScholarAI production deployment architecture
is complete and consistent with the existing source code.

## A. Existing Application Inspection

- [x] FastAPI entry point identified.
- [x] Frontend entry point identified.
- [x] PostgreSQL identified.
- [x] SQLAlchemy identified.
- [x] Psycopg identified.
- [x] pgvector identified.
- [x] Alembic identified.
- [x] Document storage service identified.
- [x] Document storage configuration identified.
- [x] JWT configuration identified.
- [x] Security middleware identified.
- [x] AI provider integration identified.
- [x] Recommendation services identified.
- [x] Opportunity provider integration identified.

## B. Architecture Design

- [x] Frontend deployment model documented.
- [x] Backend deployment model documented.
- [x] Database architecture documented.
- [x] Vector database architecture documented.
- [x] Document storage architecture documented.
- [x] Container boundaries documented.
- [x] Network boundaries documented.
- [x] Migration strategy documented.
- [x] Security boundaries documented.
- [x] Health check requirements documented.

## C. Infrastructure Decisions

- [x] Static frontend selected.
- [x] FastAPI container selected.
- [x] PostgreSQL with pgvector retained.
- [x] Persistent document storage required.
- [x] Controlled migrations selected.
- [x] Single-origin initial topology selected.
- [x] Provider-independent deployment selected.
- [x] Technical risks documented.

## D. Deferred Decisions

- [ ] Hosting provider selected.
- [ ] Production region selected.
- [ ] Production domain selected.
- [ ] TLS provider selected.
- [ ] Managed database provider selected.
- [ ] Object storage decision finalized.
- [ ] Monitoring provider selected.
- [ ] Backup retention policy finalized.

These are intentionally assigned to later Phase 21 subphases.

## E. Architecture Verification

The following must be verified before actual production deployment:

- [ ] Production dependency manifest validated.
- [ ] Backend image builds successfully.
- [ ] Frontend image builds successfully.
- [ ] PostgreSQL pgvector extension initializes.
- [ ] Alembic migration graph is valid.
- [ ] Persistent document storage survives container replacement.
- [ ] Backend connects to PostgreSQL.
- [ ] Frontend API requests use the production origin.
- [ ] Health endpoints respond correctly.
- [ ] Existing automated tests pass.

## Completion Rule

Phase 21.1 architecture design is complete when sections A,
B and C are satisfied.

Actual deployment and infrastructure verification are completed
in later Phase 21 subphases.

Do not mark Phase 21.1 production deployment as complete merely
because the architecture documents exist.
