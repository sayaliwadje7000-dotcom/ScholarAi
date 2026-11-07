from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from time import perf_counter


class RecommendationBenchmarkError(ValueError):
    """Raised when benchmark configuration is invalid."""


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    iterations: int
    minimum_ms: float
    maximum_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float


class RecommendationBenchmark:
    """
    Measure synchronous recommendation execution latency.

    Warm-up runs are excluded from recorded measurements.
    """

    @staticmethod
    def _validate_count(
        value: int,
        field_name: str,
    ) -> None:

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise RecommendationBenchmarkError(
                f"{field_name} must be a non-negative integer."
            )

    def run(
        self,
        operation,
        iterations: int = 100,
        warmup_iterations: int = 5,
    ) -> BenchmarkResult:

        if not callable(operation):
            raise RecommendationBenchmarkError(
                "operation must be callable."
            )

        self._validate_count(
            iterations,
            "iterations",
        )

        self._validate_count(
            warmup_iterations,
            "warmup_iterations",
        )

        if iterations == 0:
            raise RecommendationBenchmarkError(
                "iterations must be greater than zero."
            )

        # Warm-up: excluded from measurements.
        for _ in range(warmup_iterations):
            operation()

        measurements = []

        for _ in range(iterations):

            start = perf_counter()

            operation()

            elapsed = perf_counter() - start

            measurements.append(
                elapsed * 1000
            )

        ordered = sorted(measurements)

        p95_index = max(
            0,
            int(0.95 * len(ordered) + 0.999999) - 1,
        )

        middle = len(ordered) // 2

        if len(ordered) % 2:
            median = ordered[middle]
        else:
            median = (
                ordered[middle - 1]
                + ordered[middle]
            ) / 2

        return BenchmarkResult(
            iterations=iterations,
            minimum_ms=min(ordered),
            maximum_ms=max(ordered),
            mean_ms=mean(ordered),
            median_ms=median,
            p95_ms=ordered[p95_index],
        )