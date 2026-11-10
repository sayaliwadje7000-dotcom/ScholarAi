# Phase 20.2 — Unit Testing Engineering

## 1. Objective

Phase 20.2 establishes reusable unit-testing infrastructure for ScholarAI.

The objective is to improve the consistency, isolation, determinism,
maintainability, and reliability of unit tests.

The implementation introduces reusable test factories, assertion utilities,
fixtures, and dedicated unit-test organization.

## 2. Architecture

The initial testing support architecture contains:

    tests/
        unit/
            __init__.py
            conftest.py
            test_testing_utilities.py
            test_testing_factories.py

        support/
            __init__.py
            factories.py
            utilities.py

## 3. Test factories

Factories reduce repetitive object initialization.

The initial implementation includes:

- EvaluationResultFactory
- EvaluationReportFactory

These factories use the existing Phase 19.10 evaluation models.

Factories support:

- Successful evaluation results.
- Failed evaluation results.
- Partial evaluation results.
- Custom metrics.
- Custom metadata.
- Mixed evaluation reports.
- Empty reports.

Factories must create valid model instances and must not bypass
production validation rules.

## 4. Assertion utilities

The testing support package includes:

### assert_mapping_contains

Verifies expected mapping keys and values.

### assert_raises_with_message

Verifies an expected exception type and message.

This helper is synchronous. Async exception assertions should use
pytest's native async-compatible exception handling.

### normalize_text

Normalizes whitespace for deterministic text comparisons.

It does not perform semantic comparison or modify application output.

## 5. Fixture strategy

The unit-test package provides reusable fixtures for:

- Passed evaluation results.
- Failed evaluation results.
- Partial evaluation results.
- Successful reports.
- Empty reports.
- Deterministic evaluation metrics.

Fixtures are defined in tests/unit/conftest.py.

The project-level tests/conftest.py is not modified.

## 6. Unit-testing principles

Each unit test should:

1. Arrange controlled inputs.
2. Execute one behavior.
3. Assert meaningful outcomes.
4. Avoid unnecessary external dependencies.
5. Remain independent of other tests.

Tests should verify both successful and unsuccessful behavior.

Boundary values and invalid inputs should be included where relevant.

## 7. Application unit-testing expansion

The testing infrastructure is reusable, but it does not automatically
provide unit coverage for every production service.

Subsequent work must inspect the actual application modules and add
focused unit tests for:

- Core business logic.
- Pydantic schemas.
- Validation utilities.
- Authentication services.
- Authorization rules.
- Document-processing logic.
- Retrieval and ranking logic.
- Recommendation scoring.
- Resource discovery.
- Opportunity processing.
- LLM prompt construction.
- Provider adapters.
- Error handling.

Existing tests must be preserved.

## 8. External dependencies

Unit tests should isolate:

- Databases.
- External HTTP APIs.
- LLM providers.
- Embedding providers.
- Filesystem dependencies.
- Time-dependent behavior.
- Randomness.

Integration tests should verify actual component interactions.

Do not mistake a mocked dependency test for proof of production
integration correctness.

## 9. Test execution

Run Phase 20.2 tests:

    python -m pytest tests/unit -v

Run all test support tests:

    python -m pytest tests/unit tests/support -v

Run the complete regression suite:

    python -m pytest -v

Run coverage after verifying that pytest-cov is installed:

    python -m pytest tests/unit --cov=app --cov-report=term-missing

## 10. Acceptance criteria

Phase 20.2 requires:

- Dedicated unit-test organization.
- Reusable test factories.
- Reusable assertion helpers.
- Reusable unit-test fixtures.
- Deterministic test inputs.
- Successful focused test execution.
- No modification of existing project-wide fixtures.
- No regression in existing tests.
- Application-specific unit coverage expanded using inspected source code.

## 11. Engineering limitations

The initial factories are designed around existing evaluation models.

They are test-support utilities, not production services.

The unit-testing framework does not replace integration tests,
database tests, API tests, end-to-end tests, or Phase 19 AI evaluations.

Coverage targets must be measured against the actual project baseline.

## 12. Completion

Phase 20.2 establishes reusable unit-testing infrastructure.

Additional component-specific unit tests must be implemented based
on the actual production source code and verified through focused
and regression test execution.
