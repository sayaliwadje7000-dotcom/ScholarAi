from collections.abc import Iterable

from app.evaluation.observability.latency import (
    calculate_latency_statistics,
    calculate_throughput,
)

from app.evaluation.observability.schemas import (
    PerformanceEvaluationConfig,
    PerformanceEvaluationReport,
    PerformanceSample,
)


class PerformanceEvaluationRunner:
    def __init__(
        self,
        config: PerformanceEvaluationConfig | None = None,
    ):
        self.config = config or PerformanceEvaluationConfig()

    def evaluate(
        self,
        samples: Iterable[PerformanceSample],
    ) -> PerformanceEvaluationReport:
        samples = list(samples)

        total = len(samples)
        successful = sum(sample.success for sample in samples)
        failed = total - successful

        latencies = [sample.latency_ms for sample in samples]

        statistics = calculate_latency_statistics(latencies)

        error_rate = failed / total if total else 0.0

        input_tokens = sum(sample.input_tokens for sample in samples)
        output_tokens = sum(sample.output_tokens for sample in samples)

        costs = [
            sample.estimated_cost_usd
            for sample in samples
            if sample.estimated_cost_usd is not None
        ]

        total_cost = sum(costs)

        average_cost = total_cost / total if total else 0.0

        if samples:
            start = min(sample.timestamp for sample in samples)
            end = max(
                sample.timestamp.timestamp()
                + sample.latency_ms / 1000
                for sample in samples
            )

            elapsed_seconds = max(
                end - start.timestamp(),
                max(latencies) / 1000,
                0.000001,
            )

            throughput = calculate_throughput(
                total,
                elapsed_seconds,
            )
        else:
            throughput = 0.0

        violations = []

        if total < self.config.minimum_requests:
            violations.append("minimum_requests_not_met")

        if (
            self.config.maximum_latency_ms is not None
            and statistics["average_ms"] > self.config.maximum_latency_ms
        ):
            violations.append("maximum_average_latency_exceeded")

        if (
            self.config.maximum_p95_latency_ms is not None
            and statistics["p95_ms"]
            > self.config.maximum_p95_latency_ms
        ):
            violations.append("maximum_p95_latency_exceeded")

        if error_rate > self.config.maximum_error_rate:
            violations.append("maximum_error_rate_exceeded")

        if (
            self.config.maximum_cost_per_request_usd is not None
            and average_cost > self.config.maximum_cost_per_request_usd
        ):
            violations.append("maximum_cost_per_request_exceeded")

        return PerformanceEvaluationReport(
            total_requests=total,
            successful_requests=successful,
            failed_requests=failed,
            average_latency_ms=statistics["average_ms"],
            p50_latency_ms=statistics["p50_ms"],
            p95_latency_ms=statistics["p95_ms"],
            p99_latency_ms=statistics["p99_ms"],
            maximum_latency_ms=statistics["maximum_ms"],
            throughput_requests_per_second=throughput,
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            total_estimated_cost_usd=total_cost,
            average_cost_per_request_usd=average_cost,
            error_rate=error_rate,
            passed=not violations,
            violations=violations,
            samples=samples,
        )
