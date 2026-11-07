import asyncio

import pytest

from app.services.educational_resources.discovery_benchmark import (
    BenchmarkResult,
    DiscoveryBenchmark,
)


@pytest.mark.asyncio
async def test_benchmark_successful_operation():
    async def operation():
        await asyncio.sleep(0.001)

    result = await DiscoveryBenchmark.run(
        operation=operation,
        iterations=5,
        warmup_iterations=1,
    )

    assert isinstance(result, BenchmarkResult)

    assert result.iterations == 5
    assert result.warmup_iterations == 1

    assert result.successful_iterations == 5
    assert result.failed_iterations == 0

    assert result.minimum_ms >= 0
    assert result.maximum_ms >= result.minimum_ms
    assert result.mean_ms >= 0
    assert result.median_ms >= 0
    assert result.p95_ms >= 0


@pytest.mark.asyncio
async def test_benchmark_records_failed_iterations():
    calls = 0

    async def operation():
        nonlocal calls

        calls += 1

        if calls % 2 == 0:
            raise RuntimeError(
                "Simulated discovery failure."
            )

    result = await DiscoveryBenchmark.run(
        operation=operation,
        iterations=4,
        warmup_iterations=0,
    )

    assert result.iterations == 4

    assert result.successful_iterations == 2
    assert result.failed_iterations == 2

    assert result.error_types["RuntimeError"] == 2


@pytest.mark.asyncio
async def test_benchmark_all_iterations_fail():
    async def operation():
        raise RuntimeError("Failure")

    result = await DiscoveryBenchmark.run(
        operation=operation,
        iterations=3,
        warmup_iterations=0,
    )

    assert result.successful_iterations == 0
    assert result.failed_iterations == 3

    assert result.minimum_ms is None
    assert result.maximum_ms is None
    assert result.mean_ms is None


@pytest.mark.asyncio
async def test_benchmark_rejects_zero_iterations():
    async def operation():
        return None

    with pytest.raises(ValueError):
        await DiscoveryBenchmark.run(
            operation,
            iterations=0,
        )


@pytest.mark.asyncio
async def test_benchmark_rejects_invalid_operation():
    with pytest.raises(TypeError):
        await DiscoveryBenchmark.run(
            operation=None,
            iterations=2,
        )


@pytest.mark.asyncio
async def test_benchmark_rejects_negative_warmup():
    async def operation():
        return None

    with pytest.raises(ValueError):
        await DiscoveryBenchmark.run(
            operation,
            iterations=2,
            warmup_iterations=-1,
        )


@pytest.mark.asyncio
async def test_warmup_failure_propagates():
    async def operation():
        raise RuntimeError("Warmup failed")

    with pytest.raises(RuntimeError):
        await DiscoveryBenchmark.run(
            operation,
            iterations=2,
            warmup_iterations=1,
        )


def test_percentile_calculation():
    values = [
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
        6.0,
        7.0,
        8.0,
        9.0,
        10.0,
    ]

    result = DiscoveryBenchmark._percentile(
        values,
        0.95,
    )

    assert result == 10.0