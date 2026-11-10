# Phase 20.3 — Integration Testing

## 1. Objective

Phase 20.3 validates the interaction between ScholarAI application
components.

The objective is to identify failures at component boundaries that
may not be detected by isolated unit tests.

## 2. Existing Integration Coverage

The following existing test suites are retained.

| Area | Existing test coverage |
|---|---|
| RAG API | tests/test_rag_api.py |
| RAG service | tests/services/rag/test_rag_service.py |
| RAG reliability | tests/services/rag/test_rag_reliability.py |
| Document database | tests/test_document_database_integration.py |
| Document reliability | tests/test_document_reliability_integration.py |
| Document status | tests/test_document_status_integration.py |
| Authentication | tests/auth/test_authentication_dependency.py |
| Authorization | tests/security/test_rbac_authorization_matrix.py |
| Chat | tests/services/test_chat_integration.py |
| Opportunities | tests/services/opportunities/test_pipeline_integration.py |
| Hybrid recommendations | tests/services/recommendations/hybrid/integration/ |

## 3. New Integration Coverage

### 3.1 RAG dependency wiring

File:

tests/integration/test_rag_dependency_wiring.py

Validates:

- Embedding service dependency construction.
- Retrieval service dependency construction.
- RAG service dependency construction.
- Correct component wiring.
- Cached service reuse.
- Cache clearing and service reconstruction.

### 3.2 RAG dependency failure isolation

File:

tests/integration/test_rag_dependency_failures.py

Validates:

- Embedding service initialization failure.
- Retrieval service initialization failure.
- RAG service initialization failure.
- Failed initialization does not populate the dependency cache.

## 4. Integration Architecture

The RAG dependency construction chain is:

EmbeddingService
       |
       v
RetrievalService
       |
       v
RAGService
       |
       v
RAG API endpoint

The existing API tests separately validate authenticated requests,
request validation, response contracts, and service failures.

## 5. Testing Principles

1. Test real component boundaries wherever practical.
2. Mock external infrastructure when it is not the subject of the test.
3. Never connect automated tests to production databases.
4. Preserve existing database integration opt-in controls.
5. Keep unit and integration tests independently executable.
6. Avoid duplicating existing integration coverage.
7. Verify error propagation and failure isolation.
8. Preserve existing pytest configuration.

## 6. Database Integration Safety

Database integration tests must continue to respect the existing
SCHOLARAI_RUN_DATABASE_INTEGRATION environment variable.

Do not enable database integration tests against a production
database.

## 7. Execution Commands

Focused new integration tests:

python -m pytest tests/integration -v

Existing RAG integration coverage:

python -m pytest tests/test_rag_api.py tests/services/rag -v

Document integration coverage:

python -m pytest tests/test_document_database_integration.py tests/test_document_reliability_integration.py tests/test_document_status_integration.py -v

Authentication integration coverage:

python -m pytest tests/auth tests/security -v

Full test suite:

python -m pytest -v

## 8. Completion Criteria

- New dependency wiring tests pass.
- Dependency cache behavior is verified.
- Initialization failures are handled without caching partial services.
- Existing integration tests remain intact.
- Existing pytest configuration remains unchanged.
- Database integration safety controls remain intact.
- Full-suite regressions are investigated and resolved.

## 9. Scope Limitations

This phase adds dependency-construction integration tests. It does
not claim to perform a live end-to-end RAG workflow against an actual
embedding provider, vector database, LLM provider, or production
database.

Those infrastructure-level validations require appropriately
configured isolated test services and are not replaced by mocks.

## 10. Phase Status

Implementation: Pending test execution.

Completion must be confirmed after running the focused and full
test suites.
