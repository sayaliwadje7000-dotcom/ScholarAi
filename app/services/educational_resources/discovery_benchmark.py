from __future__ import annotations

import math
import statistics
import time

from collections import Counter
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Performance benchmark results.
    """

    iterations: int
    warmup_iterations: int
    successful_iterations: int
    failed_iterations: int

    minimum_ms: float | None
    maximum_ms: float | None
    mean_ms: float | None
    median_ms: float | None
    p95_ms: float | None

    error_types: dict[str, int]

    def __post_init__(self) -> None:
        if self.iterations <= 0:
            raise ValueError(
                "iterations must be positive."
            )

        if (
            self.successful_iterations
            + self.failed_iterations
            != self.iterations
        ):
            raise ValueError(
                "Successful and failed iterations must "
                "equal total iterations."
            )

        latency_values = (
            self.minimum_ms,
            self.maximum_ms,
            self.mean_ms,
            self.median_ms,
            self.p95_ms,
        )

        if self.successful_iterations == 0:
            if any(value is not None for value in latency_values):
                raise ValueError(
                    "Latency values must be None when "
                    "there are no successful iterations."
                )
        else:
            if any(value is None for value in latency_values):
                raise ValueError(
                    "Latency values are required when "
                    "successful iterations exist."
                )

            for value in latency_values:
                if not math.isfinite(value) or value < 0:
                    raise ValueError(
                        "Latency values must be finite "
                        "and non-negative."
                    )

    def to_dict(self) -> dict:
        return {
            "iterations": self.iterations,
            "warmup_iterations": self.warmup_iterations,
            "successful_iterations": self.successful_iterations,
            "failed_iterations": self.failed_iterations,
            "minimum_ms": self.minimum_ms,
            "maximum_ms": self.maximum_ms,
            "mean_ms": self.mean_ms,
            "median_ms": self.median_ms,
            "p95_ms": self.p95_ms,
            "error_types": dict(self.error_types),
        }


class DiscoveryBenchmark:
    """
    Benchmarks asynchronous resource discovery operations.

    The benchmark does not make assumptions about the
    implementation of the operation being measured.
    """

    @staticmethod
    def _validate_iterations(
        iterations: int,
        name: str,
        allow_zero: bool = False,
    ) -> None:
        if isinstance(iterations, bool) or not isinstance(
            iterations,
            int,
        ):
            raise TypeError(
                f"{name} must be an integer."
            )

        minimum = 0 if allow_zero else 1

        if iterations < minimum:
            raise ValueError(
                f"{name} must be at least {minimum}."
            )

    @staticmethod
    def _percentile(
        values: list[float],
        percentile: float,
    ) -> float:
        """
        Calculate nearest-rank percentile.
        """

        ordered = sorted(values)

        index = math.ceil(
            percentile * len(ordered)
        ) - 1

        index = max(
            0,
            min(index, len(ordered) - 1),
        )

        return ordered[index]

    @classmethod
    async def run(
        cls,
        operation: Callable[[], Awaitable[T]],
        iterations: int = 20,
        warmup_iterations: int = 2,
    ) -> BenchmarkResult:
        """
        Benchmark an asynchronous operation.

        Exceptions during measured iterations are counted
        instead of terminating the entire benchmark.

        Warm-up exceptions are allowed to propagate because
        they indicate that the benchmark operation is not
        correctly initialized.
        """

        cls._validate_iterations(
            iterations,
            "iterations",
        )

        cls._validate_iterations(
            warmup_iterations,
            "warmup_iterations",
            allow_zero=True,
        )

        if not callable(operation):
            raise TypeError(
                "operation must be callable."
            )

        # Warm-up phase.
        for _ in range(warmup_iterations):
            await operation()

        durations = []
        error_types = Counter()

        successful_iterations = 0
        failed_iterations = 0

        # Measurement phase.
        for _ in range(iterations):
            start = time.perf_counter()

            try:
                await operation()

                elapsed_ms = (
                    time.perf_counter() - start
                ) * 1000

                durations.append(elapsed_ms)

                successful_iterations += 1

            except Exception as exc:
                failed_iterations += 1

                error_types[
                    type(exc).__name__
                ] += 1

        if durations:
            minimum_ms = min(durations)
            maximum_ms = max(durations)
            mean_ms = statistics.mean(durations)
            median_ms = statistics.median(durations)

            p95_ms = cls._percentile(
                durations,
                0.95,
            )

        else:
            minimum_ms = None
            maximum_ms = None
            mean_ms = None
            median_ms = None
            p95_ms = None

        return BenchmarkResult(
            iterations=iterations,
            warmup_iterations=warmup_iterations,
            successful_iterations=successful_iterations,
            failed_iterations=failed_iterations,
            minimum_ms=minimum_ms,
            maximum_ms=maximum_ms,
            mean_ms=mean_ms,
            median_ms=median_ms,
            p95_ms=p95_ms,
            error_types=dict(error_types),
        )