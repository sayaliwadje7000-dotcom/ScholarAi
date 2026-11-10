# Phase 20.6 - End-to-End Workflow Testing

## Objective

Validate important application workflows through the FastAPI application
using HTTP requests.

## Implemented Test Modules

| File | Purpose |
|---|---|
| tests/e2e/__init__.py | E2E test package |
| tests/e2e/conftest.py | Reusable HTTP test client |
| tests/e2e/test_application_workflow.py | Application startup and health |
| tests/e2e/test_api_availability_workflow.py | API and OpenAPI availability |
| tests/e2e/test_rag_workflow.py | RAG request validation |
| tests/e2e/test_application_regression.py | Core application regression |

## Coverage

### Application Workflow
- Root endpoint availability.
- Health endpoint availability.
- JSON response validation.

### API Availability
- OpenAPI schema availability.
- API documentation availability.
- Registered API operations.

### RAG Workflow
- RAG endpoint discovery through OpenAPI.
- Unauthenticated request rejection.
- Invalid query rejection.
- Invalid limit rejection.

### Regression
- Core routes remain registered.
- RAG route remains registered.
- OpenAPI metadata remains available.

## Execution

Run E2E tests:

    python -m pytest tests/e2e -v

Run RAG API regression tests:

    python -m pytest tests/test_rag_api.py -v

Run the complete suite:

    python -m pytest -v

## Scope Limitations

These tests validate application-level HTTP workflows and request rejection.

They do not establish a complete authenticated student journey involving
real PostgreSQL records, PDF uploads, embedding generation, retrieval,
LLM generation, and personalized recommendations.

Those workflows require dedicated fixtures and isolated test infrastructure.

## Completion Criteria

- E2E test modules are present.
- Application and health checks pass.
- OpenAPI checks pass.
- RAG request validation passes.
- Regression checks pass.
- Existing tests remain passing.
- Full test suite has no newly introduced regressions.

## Status

Phase 20.6 must not be marked complete until its tests have been executed
and their results reviewed.
