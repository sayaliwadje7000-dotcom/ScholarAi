import asyncio
import time

import pytest

from app.services.embeddings.retrieval_benchmark import (
    benchmark_callable,
    benchmark_async_callable,
)


def test_sync_benchmark():
    def sample_function():
        time.sleep(0.001)

    result = benchmark_callable(
        sample_function,
        iterations=5,
        warmup_iterations=2,
    )

    assert result.iterations == 5
    assert result.warmup_iterations == 2
    assert result.mean_latency_ms > 0
    assert result.median_latency_ms > 0
    assert result.p95_latency_ms > 0
    assert result.minimum_latency_ms > 0
    assert result.maximum_latency_ms >= result.minimum_latency_ms
    assert result.throughput_per_second > 0


def test_sync_benchmark_without_warmup():
    result = benchmark_callable(
        lambda: sum(range(100)),
        iterations=3,
        warmup_iterations=0,
    )

    assert result.iterations == 3
    assert result.warmup_iterations == 0


def test_async_benchmark():
    async def sample_function():
        await asyncio.sleep(0.001)

    result = asyncio.run(
        benchmark_async_callable(
            sample_function,
            iterations=5,
            warmup_iterations=2,
        )
    )

    assert result.iterations == 5
    assert result.warmup_iterations == 2
    assert result.mean_latency_ms > 0
    assert result.p95_latency_ms > 0
    assert result.throughput_per_second > 0


def test_sync_benchmark_rejects_async_callable():
    async def sample_function():
        return None

    with pytest.raises(TypeError):
        benchmark_callable(sample_function, iterations=2)


def test_invalid_sync_iterations_rejected():
    with pytest.raises(ValueError):
        benchmark_callable(lambda: None, iterations=0)


def test_invalid_async_iterations_rejected():
    async def run():
        await benchmark_async_callable(
            lambda: None,
            iterations=0,
        )

    with pytest.raises(ValueError):
        asyncio.run(run())


def test_negative_warmup_rejected():
    with pytest.raises(ValueError):
        benchmark_callable(
            lambda: None,
            iterations=2,
            warmup_iterations=-1,
        )


def test_non_callable_rejected():
    with pytest.raises(TypeError):
        benchmark_callable(None, iterations=2)