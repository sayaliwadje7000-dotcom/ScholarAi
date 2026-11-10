# ScholarAI Testing Guide

## 1. Overview

The ScholarAI test suite verifies the correctness, reliability, security,
and performance of the application.

Testing is organized into layers so that individual components and
complete workflows can be verified independently.

The detailed architecture is documented in:

- docs/phase-20-1-testing-architecture.md
- docs/testing-quality-gates.md

---

## 2. Running Tests

Run the complete test suite from the project root.

PowerShell:

    $env:PYTHONPATH = (Get-Location).Path
    python -m pytest -v

Run a specific test directory:

    python -m pytest tests/evaluation -v

Run one test file:

    python -m pytest tests/test_api.py -v

Run one test function:

    python -m pytest tests/test_api.py::test_home_endpoint -v

Run tests with short tracebacks:

    python -m pytest -v --tb=short

Do not use the bare pytest executable when the project virtual
environment is active but command resolution is uncertain.

Prefer:

    python -m pytest

---

## 3. Existing Test Domains

ScholarAI already contains tests for several application domains.

The existing structure must be preserved until each directory has
been inspected and an explicit reorganization plan has been approved.

Important test domains include:

- API tests.
- Authentication and security tests.
- Document processing tests.
- RAG and retrieval tests.
- Recommendation tests.
- Educational resource discovery tests.
- Opportunity discovery tests.
- AI evaluation tests.
- Optimization tests.
- Statistical experiment tests.
- Scoring tests.

New tests should be placed alongside the relevant domain until the
formal test organization is implemented.

---

## 4. Test Naming

Use descriptive test names.

Examples:

    test_user_can_login_with_valid_credentials

    test_login_rejects_invalid_password

    test_document_upload_rejects_unsupported_extension

    test_rag_returns_relevant_context

    test_user_cannot_access_another_users_document

Test names should describe expected behavior.

Avoid names such as:

    test_function_1

    test_service

    test_success

---

## 5. Test Independence

Each test should:

- Arrange its own required state.
- Execute the behavior under examination.
- Assert meaningful outcomes.
- Clean up temporary resources.
- Avoid relying on other tests.

Tests should not depend on execution order.

---

## 6. Test Data

Use synthetic test data.

Do not use:

- Real student passwords.
- Production access tokens.
- Real private documents.
- Production database records.
- Unredacted user information.

Use temporary files and isolated test databases where appropriate.

---

## 7. External Dependencies

Tests must distinguish between:

- Unit tests with controlled dependencies.
- Integration tests with isolated services.
- Explicit live integration tests.

Live external API calls should not run implicitly in the default
offline regression suite.

---

## 8. Assertions

Assertions must verify expected application behavior.

Prefer:

    assert response.status_code == 200
    assert response.json()["status"] == "success"

Avoid relying only on:

    assert response is not None

Use approximate comparisons for floating-point values.

Verify error responses and failure paths in addition to successful paths.

---

## 9. Test Failure Handling

When a test fails:

1. Read the complete traceback.
2. Identify the failing test.
3. Determine whether the problem is in production code, test code,
   environment configuration, or an external dependency.
4. Reproduce the failure.
5. Correct the root cause.
6. Rerun the focused test.
7. Rerun relevant regression tests.

Do not change correct application behavior merely to satisfy an
incorrect test expectation.

Do not remove meaningful assertions to make a test pass.

---

## 10. Coverage

Coverage will be introduced and enforced after the current project
baseline has been measured.

Initial targets are documented in:

    docs/testing-quality-gates.md

Coverage is a supporting quality metric, not proof of correctness.

---

## 11. Development Workflow

For each testing subphase:

1. Inspect relevant existing implementation.
2. Inspect existing tests and fixtures.
3. Identify missing coverage.
4. Add focused tests.
5. Execute focused tests.
6. Resolve failures.
7. Execute relevant regression tests.
8. Review changed files.
9. Run git diff --check.
10. Commit only after verification.

---

## 12. Important Engineering Rule

Do not replace, delete, or reorganize existing ScholarAI tests
without reviewing their purpose and dependencies.

Preserve existing test coverage while incrementally improving
the testing architecture.
