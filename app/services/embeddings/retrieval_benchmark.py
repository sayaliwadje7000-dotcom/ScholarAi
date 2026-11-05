from __future__ import annotations

import asyncio
import inspect
import statistics
import time

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    iterations: int
    warmup_iterations: int
    mean_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    minimum_latency_ms: float
    maximum_latency_ms: float
    throughput_per_second: float


def _validate_iterations(
    iterations: int,
    warmup_iterations: int,
) -> None:
    if (
        isinstance(iterations, bool)
        or not isinstance(iterations, int)
        or iterations <= 0
    ):
        raise ValueError("iterations must be a positive integer.")

    if (
        isinstance(warmup_iterations, bool)
        or not isinstance(warmup_iterations, int)
        or warmup_iterations < 0
    ):
        raise ValueError(
            "warmup_iterations must be a non-negative integer."
        )


def _percentile(values: list[float], percentile: float) -> float:
    """Calculate percentile using linear interpolation."""

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * percentile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)

    fraction = position - lower_index

    return (
        ordered[lower_index] * (1 - fraction)
        + ordered[upper_index] * fraction
    )


def _build_result(
    latencies: list[float],
    warmup_iterations: int,
    total_elapsed_seconds: float,
) -> BenchmarkResult:
    total_latency = sum(latencies)

    return BenchmarkResult(
        iterations=len(latencies),
        warmup_iterations=warmup_iterations,
        mean_latency_ms=statistics.mean(latencies),
        median_latency_ms=statistics.median(latencies),
        p95_latency_ms=_percentile(latencies, 0.95),
        minimum_latency_ms=min(latencies),
        maximum_latency_ms=max(latencies),
        throughput_per_second=(
            len(latencies) / total_elapsed_seconds
            if total_elapsed_seconds > 0
            else 0.0
        ),
    )


def benchmark_callable(
    function: Callable[[], Any],
    iterations: int = 100,
    warmup_iterations: int = 5,
) -> BenchmarkResult:
    """
    Benchmark a synchronous callable.

    Awaitable results are rejected. Use benchmark_async_callable
    for asynchronous functions.
    """

    _validate_iterations(iterations, warmup_iterations)

    if not callable(function):
        raise TypeError("function must be callable.")

    for _ in range(warmup_iterations):
        result = function()

        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()

            raise TypeError(
                "An asynchronous callable requires benchmark_async_callable."
            )

    latencies: list[float] = []

    total_start = time.perf_counter()

    for _ in range(iterations):
        start = time.perf_counter()

        result = function()

        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()

            raise TypeError(
                "An asynchronous callable requires benchmark_async_callable."
            )

        elapsed = time.perf_counter() - start
        latencies.append(elapsed * 1000)

    total_elapsed = time.perf_counter() - total_start

    return _build_result(
        latencies,
        warmup_iterations,
        total_elapsed,
    )


async def benchmark_async_callable(
    function: Callable[[], Any],
    iterations: int = 100,
    warmup_iterations: int = 5,
) -> BenchmarkResult:
    """
    Benchmark an asynchronous callable sequentially.

    Supports both async functions and synchronous functions
    returning awaitable results.
    """

    _validate_iterations(iterations, warmup_iterations)

    if not callable(function):
        raise TypeError("function must be callable.")

    async def execute() -> None:
        result = function()

        if inspect.isawaitable(result):
            await result

    for _ in range(warmup_iterations):
        await execute()

    latencies: list[float] = []

    total_start = time.perf_counter()

    for _ in range(iterations):
        start = time.perf_counter()

        await execute()

        elapsed = time.perf_counter() - start
        latencies.append(elapsed * 1000)

    total_elapsed = time.perf_counter() - total_start

    return _build_result(
        latencies,
        warmup_iterations,
        total_elapsed,
    )