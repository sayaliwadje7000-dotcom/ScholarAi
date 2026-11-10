import pytest

from tests.concurrency.performance_metrics import (
    calculate_latency_metrics,
    measure_execution_time,
)


def test_latency_metrics_calculation():
    latencies = [0.1, 0.2, 0.3, 0.4, 0.5]

    metrics = calculate_latency_metrics(latencies)

    assert metrics["request_count"] == 5
    assert metrics["minimum_seconds"] == 0.1
    assert metrics["maximum_seconds"] == 0.5
    assert metrics["median_seconds"] == 0.3
    assert metrics["p95_seconds"] == 0.5


def test_latency_metrics_reject_empty_input():
    with pytest.raises(
        ValueError,
        match="At least one latency measurement is required",
    ):
        calculate_latency_metrics([])


def test_latency_metrics_reject_negative_values():
    with pytest.raises(
        ValueError,
        match="Latency measurements cannot be negative",
    ):
        calculate_latency_metrics([0.1, -0.2, 0.3])


def test_measure_execution_time_returns_result_and_duration():
    def operation():
        return "ScholarAI"

    result, elapsed = measure_execution_time(operation)

    assert result == "ScholarAI"
    assert elapsed >= 0
