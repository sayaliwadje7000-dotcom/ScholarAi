from datetime import datetime, timedelta, timezone

from app.evaluation.observability.runner import PerformanceEvaluationRunner
from app.evaluation.observability.schemas import (
    PerformanceEvaluationConfig,
    PerformanceSample,
)


def make_samples():
    start = datetime.now(timezone.utc)

    return [
        PerformanceSample(
            sample_id=f"sample-{index}",
            component="llm",
            operation="generate",
            timestamp=start + timedelta(seconds=index),
            latency_ms=latency,
            success=success,
            input_tokens=100,
            output_tokens=200,
            estimated_cost_usd=0.01,
        )
        for index, (latency, success) in enumerate(
            [
                (100, True),
                (200, True),
                (300, False),
                (400, True),
                (500, True),
            ]
        )
    ]


def test_runner_evaluates_samples():
    runner = PerformanceEvaluationRunner()

    report = runner.evaluate(make_samples())

    assert report.total_requests == 5
    assert report.successful_requests == 4
    assert report.failed_requests == 1
    assert report.error_rate == 0.2
    assert report.average_latency_ms == 300
    assert report.total_input_tokens == 500
    assert report.total_output_tokens == 1000
    assert report.total_estimated_cost_usd == 0.05


def test_runner_calculates_percentiles():
    report = PerformanceEvaluationRunner().evaluate(make_samples())

    assert report.p50_latency_ms == 300
    assert report.p95_latency_ms == 480
    assert report.p99_latency_ms == 496


def test_runner_passes_valid_thresholds():
    config = PerformanceEvaluationConfig(
        maximum_latency_ms=500,
        maximum_p95_latency_ms=500,
        maximum_error_rate=0.2,
        maximum_cost_per_request_usd=0.01,
    )

    report = PerformanceEvaluationRunner(config).evaluate(make_samples())

    assert report.passed is True
    assert report.violations == []


def test_runner_detects_latency_violation():
    config = PerformanceEvaluationConfig(
        maximum_latency_ms=200,
    )

    report = PerformanceEvaluationRunner(config).evaluate(make_samples())

    assert report.passed is False
    assert "maximum_average_latency_exceeded" in report.violations


def test_runner_detects_p95_violation():
    config = PerformanceEvaluationConfig(
        maximum_p95_latency_ms=400,
    )

    report = PerformanceEvaluationRunner(config).evaluate(make_samples())

    assert "maximum_p95_latency_exceeded" in report.violations


def test_runner_detects_error_rate_violation():
    config = PerformanceEvaluationConfig(
        maximum_error_rate=0.1,
    )

    report = PerformanceEvaluationRunner(config).evaluate(make_samples())

    assert "maximum_error_rate_exceeded" in report.violations


def test_runner_detects_cost_violation():
    config = PerformanceEvaluationConfig(
        maximum_cost_per_request_usd=0.005,
    )

    report = PerformanceEvaluationRunner(config).evaluate(make_samples())

    assert "maximum_cost_per_request_exceeded" in report.violations


def test_runner_detects_insufficient_samples():
    config = PerformanceEvaluationConfig(minimum_requests=10)

    report = PerformanceEvaluationRunner(config).evaluate(make_samples())

    assert "minimum_requests_not_met" in report.violations


def test_runner_handles_empty_samples():
    report = PerformanceEvaluationRunner().evaluate([])

    assert report.total_requests == 0
    assert report.average_latency_ms == 0
    assert report.error_rate == 0
    assert report.passed is False
    assert "minimum_requests_not_met" in report.violations
