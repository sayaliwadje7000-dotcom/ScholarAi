import pytest

from app.services.recommendations.content_based.benchmark import (
    RecommendationBenchmark,
    RecommendationBenchmarkError,
)


@pytest.fixture
def benchmark():
    return RecommendationBenchmark()


def test_benchmark_returns_latency_metrics(benchmark):

    result = benchmark.run(
        operation=lambda: sum(range(100)),
        iterations=10,
        warmup_iterations=2,
    )

    assert result.iterations == 10
    assert result.minimum_ms >= 0
    assert result.maximum_ms >= result.minimum_ms
    assert result.mean_ms >= 0
    assert result.median_ms >= 0
    assert result.p95_ms >= 0


def test_warmup_iterations_are_excluded(benchmark):

    calls = []

    def operation():
        calls.append(1)

    result = benchmark.run(
        operation=operation,
        iterations=5,
        warmup_iterations=3,
    )

    assert len(calls) == 8
    assert result.iterations == 5


def test_benchmark_rejects_non_callable(benchmark):

    with pytest.raises(
        RecommendationBenchmarkError
    ):
        benchmark.run(
            operation=None,
            iterations=5,
        )


def test_benchmark_rejects_zero_iterations(benchmark):

    with pytest.raises(
        RecommendationBenchmarkError
    ):
        benchmark.run(
            operation=lambda: None,
            iterations=0,
        )


def test_benchmark_rejects_negative_iterations(benchmark):

    with pytest.raises(
        RecommendationBenchmarkError
    ):
        benchmark.run(
            operation=lambda: None,
            iterations=-1,
        )


def test_benchmark_propagates_operation_errors(benchmark):

    def failing_operation():
        raise RuntimeError("Benchmark failure")

    with pytest.raises(RuntimeError):
        benchmark.run(
            operation=failing_operation,
            iterations=2,
            warmup_iterations=0,
        )