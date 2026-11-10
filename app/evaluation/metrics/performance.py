import math
from statistics import mean, median


def _percentile(values, percentile):
    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return ordered[lower]

    fraction = position - lower

    return (
        ordered[lower] * (1 - fraction)
        + ordered[upper] * fraction
    )


def latency_statistics(durations):
    if not durations:
        raise ValueError("Durations cannot be empty.")

    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        for value in durations
    ):
        raise ValueError("Durations must be finite non-negative numbers.")

    return {
        "mean": mean(durations),
        "median": median(durations),
        "p50": _percentile(durations, 0.50),
        "p90": _percentile(durations, 0.90),
        "p95": _percentile(durations, 0.95),
        "p99": _percentile(durations, 0.99),
        "min": min(durations),
        "max": max(durations),
    }


def reliability(succeeded, failed, timed_out):
    values = [succeeded, failed, timed_out]

    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        for value in values
    ):
        raise ValueError("Counts must be non-negative integers.")

    total = sum(values)

    if total == 0:
        raise ValueError("Total execution count cannot be zero.")

    return {
        "success_rate": succeeded / total,
        "failure_rate": failed / total,
        "timeout_rate": timed_out / total,
    }