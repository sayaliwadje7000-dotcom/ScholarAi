import math
import random
from collections.abc import Sequence

from app.evaluation.experiments.exceptions import (
    ExperimentValidationError,
)


def _validate_values(values: Sequence[float]) -> list[float]:
    result = [float(value) for value in values]

    if not result:
        raise ExperimentValidationError(
            "At least one numerical observation is required."
        )

    if any(not math.isfinite(value) for value in result):
        raise ExperimentValidationError(
            "Observations must contain finite numerical values."
        )

    return result


def mean(values: Sequence[float]) -> float:
    data = _validate_values(values)
    return sum(data) / len(data)


def median(values: Sequence[float]) -> float:
    data = sorted(_validate_values(values))
    count = len(data)
    middle = count // 2

    if count % 2:
        return data[middle]

    return (data[middle - 1] + data[middle]) / 2


def variance(
    values: Sequence[float],
    sample: bool = True,
) -> float:
    data = _validate_values(values)

    if sample and len(data) < 2:
        raise ExperimentValidationError(
            "Sample variance requires at least two observations."
        )

    center = sum(data) / len(data)
    denominator = len(data) - 1 if sample else len(data)

    return sum((value - center) ** 2 for value in data) / denominator


def standard_deviation(
    values: Sequence[float],
    sample: bool = True,
) -> float:
    return math.sqrt(variance(values, sample=sample))


def standard_error(values: Sequence[float]) -> float:
    data = _validate_values(values)

    if len(data) < 2:
        raise ExperimentValidationError(
            "Standard error requires at least two observations."
        )

    return standard_deviation(data) / math.sqrt(len(data))


def percentile(
    values: Sequence[float],
    percentile_value: float,
) -> float:
    data = sorted(_validate_values(values))

    if not 0 <= percentile_value <= 100:
        raise ExperimentValidationError(
            "Percentile must be between 0 and 100."
        )

    if len(data) == 1:
        return data[0]

    position = (len(data) - 1) * percentile_value / 100

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return data[lower]

    weight = position - lower

    return (
        data[lower] * (1 - weight)
        + data[upper] * weight
    )


def confidence_interval(
    values: Sequence[float],
    confidence_level: float = 0.95,
) -> tuple[float, float]:
    data = _validate_values(values)

    if len(data) < 2:
        raise ExperimentValidationError(
            "Confidence intervals require at least two observations."
        )

    critical_values = {
        0.90: 1.6448536269514722,
        0.95: 1.959963984540054,
        0.99: 2.5758293035489004,
    }

    critical = critical_values.get(confidence_level)

    if critical is None:
        raise ExperimentValidationError(
            "Supported confidence levels are 0.90, 0.95 and 0.99."
        )

    center = mean(data)
    margin = critical * standard_error(data)

    return center - margin, center + margin


def bootstrap_mean_difference(
    differences: Sequence[float],
    iterations: int = 5000,
    confidence_level: float = 0.95,
    random_seed: int = 42,
) -> tuple[float, float]:
    data = _validate_values(differences)

    if len(data) < 2:
        raise ExperimentValidationError(
            "Bootstrap comparison requires at least two paired samples."
        )

    if iterations < 100:
        raise ExperimentValidationError(
            "At least 100 bootstrap iterations are required."
        )

    if not 0 < confidence_level < 1:
        raise ExperimentValidationError(
            "Confidence level must be between 0 and 1."
        )

    generator = random.Random(random_seed)
    bootstrap_means = []

    for _ in range(iterations):
        sample = [
            generator.choice(data)
            for _ in range(len(data))
        ]

        bootstrap_means.append(sum(sample) / len(sample))

    tail = (1 - confidence_level) * 50

    return (
        percentile(bootstrap_means, tail),
        percentile(bootstrap_means, 100 - tail),
    )


def normal_two_sided_p_value(
    observed_mean: float,
    observed_standard_error: float,
) -> float:
    if observed_standard_error < 0:
        raise ExperimentValidationError(
            "Standard error cannot be negative."
        )

    if observed_standard_error == 0:
        return 1.0 if observed_mean == 0 else 0.0

    z_score = abs(observed_mean / observed_standard_error)

    return math.erfc(z_score / math.sqrt(2))


def paired_effect_size(
    differences: Sequence[float],
) -> float:
    data = _validate_values(differences)

    if len(data) < 2:
        raise ExperimentValidationError(
            "Effect size requires at least two paired observations."
        )

    deviation = standard_deviation(data)

    if deviation == 0:
        return 0.0 if mean(data) == 0 else math.copysign(
            float("inf"),
            mean(data),
        )

    return mean(data) / deviation
