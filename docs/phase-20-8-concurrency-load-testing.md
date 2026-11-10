# Phase 20.8 - Concurrency and Load Testing

## 1. Objective

Evaluate ScholarAI behavior under simultaneous and repeated HTTP requests.

The purpose is to identify request failures, concurrency instability,
and performance regressions.

## 2. Implemented Modules

| File | Purpose |
|---|---|
| tests/concurrency/__init__.py | Concurrency testing package |
| tests/concurrency/test_concurrent_api_requests.py | Concurrent API requests |
| tests/concurrency/test_concurrent_openapi_requests.py | Concurrent OpenAPI requests |
| tests/concurrency/test_api_request_stability.py | Repeated request stability |
| tests/concurrency/test_bounded_load.py | Bounded concurrent load |
| tests/concurrency/performance_metrics.py | Performance measurement utilities |
| tests/concurrency/test_performance_metrics.py | Performance utility tests |

## 3. Concurrent API Testing

Tests cover:

- Simultaneous root endpoint requests.
- Simultaneous health endpoint requests.
- Successful HTTP responses.
- JSON response validation.

## 4. OpenAPI Concurrency Testing

Tests cover:

- Concurrent OpenAPI requests.
- Schema availability.
- Consistency of registered API paths.

## 5. Request Stability

Tests cover:

- Repeated root endpoint requests.
- Repeated health endpoint requests.
- Non-negative request latency.

## 6. Bounded Load Testing

The controlled test workload includes:

- Five concurrent workers.
- Ten requests per worker.
- Fifty total root endpoint requests.
- Twenty-five concurrent health endpoint requests.

These are development-level smoke-load tests, not production capacity benchmarks.

## 7. Performance Metrics

The performance utility calculates:

- Request count.
- Minimum latency.
- Maximum latency.
- Mean latency.
- Median latency.
- 95th percentile latency.

All latency values are measured in seconds.

## 8. Execution Commands

Run concurrency tests:

    python -m pytest tests/concurrency -v

Run API regression tests:

    python -m pytest tests/test_rag_api.py -v

Run concurrency and E2E tests:

    python -m pytest tests/concurrency tests/e2e -v

Run the complete suite:

    python -m pytest -v

## 9. Important Limitations

These tests use FastAPI TestClient and a bounded number of requests.

They do not establish:

- Production requests per second.
- Maximum concurrent users.
- Database connection pool capacity.
- Memory consumption under sustained load.
- CPU utilization under load.
- Multi-process deployment behavior.
- Distributed concurrency behavior.
- Production latency service-level objectives.

A dedicated load-testing tool and deployed environment are needed for those measurements.

## 10. Completion Criteria

- Concurrent API tests pass.
- Concurrent OpenAPI tests pass.
- Repeated request tests pass.
- Bounded load tests pass.
- Performance utility tests pass.
- Existing API tests remain passing.
- Full test suite has no newly introduced regressions.

## 11. Phase Status

Phase 20.8 is complete only after test execution and result review.
