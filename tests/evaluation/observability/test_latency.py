import pytest

from app.evaluation.observability.latency import (
    average_latency,
    calculate_latency_statistics,
    calculate_throughput,
    maximum_latency,
    percentile,
)


def test_percentile_interpolation():
    assert percentile([10, 20, 30, 40, 50], 50) == 30


def test_percentile_boundaries():
    assert percentile([10, 20, 30], 0) == 10
    assert percentile([10, 20, 30], 100) == 30


def test_percentile_empty_values():
    assert percentile([], 95) == 0


def test_percentile_rejects_invalid_percentile():
    with pytest.raises(ValueError):
        percentile([10, 20], 110)


def test_average_latency():
    assert average_latency([10, 20, 30]) == 20


def test_average_latency_empty():
    assert average_latency([]) == 0


def test_maximum_latency():
    assert maximum_latency([10, 50, 20]) == 50


def test_latency_statistics():
    result = calculate_latency_statistics([10, 20, 30, 40, 50])

    assert result["average_ms"] == 30
    assert result["p50_ms"] == 30
    assert result["p95_ms"] == 48
    assert result["p99_ms"] == 49.6
    assert result["maximum_ms"] == 50


def test_throughput():
    assert calculate_throughput(100, 10) == 10


def test_throughput_zero_elapsed_time():
    assert calculate_throughput(10, 0) == 0


def test_throughput_rejects_negative_values():
    with pytest.raises(ValueError):
        calculate_throughput(-1, 10)
