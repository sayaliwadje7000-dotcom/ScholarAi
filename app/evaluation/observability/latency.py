from collections.abc import Iterable


def percentile(values: Iterable[float], percentile_value: float) -> float:
    values = sorted(float(value) for value in values)

    if not values:
        return 0.0

    if not 0 <= percentile_value <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * percentile_value / 100
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(values) - 1)

    fraction = position - lower_index

    return (
        values[lower_index]
        + fraction * (values[upper_index] - values[lower_index])
    )


def average_latency(values: Iterable[float]) -> float:
    values = [float(value) for value in values]

    if not values:
        return 0.0

    return sum(values) / len(values)


def maximum_latency(values: Iterable[float]) -> float:
    values = [float(value) for value in values]

    return max(values, default=0.0)


def calculate_latency_statistics(values: Iterable[float]) -> dict[str, float]:
    values = list(values)

    return {
        "average_ms": average_latency(values),
        "p50_ms": percentile(values, 50),
        "p95_ms": percentile(values, 95),
        "p99_ms": percentile(values, 99),
        "maximum_ms": maximum_latency(values),
    }


def calculate_throughput(
    request_count: int,
    elapsed_seconds: float,
) -> float:
    if request_count < 0:
        raise ValueError("Request count cannot be negative")

    if elapsed_seconds < 0:
        raise ValueError("Elapsed time cannot be negative")

    if request_count == 0 or elapsed_seconds == 0:
        return 0.0

    return request_count / elapsed_seconds
