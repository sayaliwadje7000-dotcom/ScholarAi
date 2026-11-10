import math
import statistics

from app.evaluation.optimization.exceptions import (
    OptimizationValidationError,
)


def validate_metric_values(
    metric_values: dict[str, list[float]],
    minimum_samples: int,
) -> None:
    if not metric_values:
        raise OptimizationValidationError(
            "Evaluator returned no metrics."
        )

    for metric_name, values in metric_values.items():
        if not metric_name.strip():
            raise OptimizationValidationError(
                "Metric names cannot be empty."
            )

        if not values:
            raise OptimizationValidationError(
                f"Metric '{metric_name}' has no observations."
            )

        if len(values) < minimum_samples:
            raise OptimizationValidationError(
                f"Metric '{metric_name}' has {len(values)} samples; "
                f"{minimum_samples} required."
            )

        for value in values:
            if not isinstance(value, (int, float)):
                raise OptimizationValidationError(
                    f"Metric '{metric_name}' contains a non-numeric value."
                )

            if not math.isfinite(value):
                raise OptimizationValidationError(
                    f"Metric '{metric_name}' contains a non-finite value."
                )


def summarize_metrics(
    metric_values: dict[str, list[float]],
) -> tuple[dict[str, float], dict[str, float], dict[str, int]]:
    means = {}
    standard_deviations = {}
    sample_counts = {}

    for metric_name, values in metric_values.items():
        means[metric_name] = statistics.mean(values)

        standard_deviations[metric_name] = (
            statistics.stdev(values) if len(values) > 1 else 0.0
        )

        sample_counts[metric_name] = len(values)

    return means, standard_deviations, sample_counts
