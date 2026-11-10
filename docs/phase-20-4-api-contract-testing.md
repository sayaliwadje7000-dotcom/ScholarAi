# Phase 20.4 — API and Contract Testing

## 1. Objective

Phase 20.4 establishes automated contract validation for ScholarAI
HTTP APIs.

The OpenAPI specification is treated as the published API contract.

Tests verify that endpoints expose consistent and resolvable
request and response definitions.

## 2. Test Architecture

tests/
    contracts/
        __init__.py
        openapi_utils.py
        test_openapi_contract.py
        test_http_operation_contract.py
        test_rag_api_contract.py

## 3. OpenAPI Contract Validation

The OpenAPI specification is inspected for:

- Valid specification structure.
- API metadata.
- Registered HTTP operations.
- Operation identifiers.
- Documented responses.
- Response descriptions.
- Component schemas.
- Resolvable local schema references.

## 4. HTTP Operation Contract Validation

HTTP operation tests inspect:

- Successful response definitions.
- Request body content.
- Response media types.
- Consistency of documented HTTP operations.

## 5. RAG API Contract Validation

The RAG API contract tests verify:

- Registered POST /ask endpoint.
- Request body availability.
- JSON request schema.
- Successful HTTP 200 response.
- JSON response schema.
- HTTP 422 validation response.
- Operation identifier.

The tests inspect the published API contract rather than invoking
external embedding or LLM providers.

## 6. Existing API Tests

Existing API behavior tests remain responsible for validating
runtime behavior, including:

- Authentication.
- Authorization.
- Request validation.
- Successful API execution.
- Error handling.
- Response payloads.
- Dependency overrides.

The new contract tests complement these tests rather than replacing
them.

## 7. Test Execution

Run the new contract tests:

python -m pytest tests/contracts -v

Run RAG API tests:

python -m pytest tests/test_rag_api.py tests/contracts/test_rag_api_contract.py -v

Run the complete API test collection:

python -m pytest tests -v

Run the complete project test suite:

python -m pytest -v

## 8. Contract Change Management

Changes to API request or response models can change the generated
OpenAPI contract.

When changing a contract:

1. Update the relevant Pydantic schema.
2. Update endpoint response models where necessary.
3. Regenerate the OpenAPI document through FastAPI.
4. Update affected contract tests.
5. Run existing API behavior tests.
6. Run the full test suite.
7. Review breaking changes before deployment.

## 9. Completion Criteria

- OpenAPI specification tests pass.
- All local schema references resolve.
- HTTP operation contracts pass.
- RAG API contract tests pass.
- Existing API behavior tests remain passing.
- No existing API configuration is overwritten.
- Full-suite regressions are investigated and resolved.

## 10. Scope Limitations

This phase validates the generated OpenAPI contract and selected
API operation definitions.

It does not establish compatibility with every external API
consumer, generate a client SDK, or guarantee backward compatibility
with previously deployed API versions.

Those activities require explicit versioning and consumer
compatibility testing.

## 11. Phase Status

Implementation: Pending test execution.

Completion must be confirmed after focused and full-suite
validation.
