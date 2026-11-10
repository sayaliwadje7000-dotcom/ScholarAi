from statistics import mean, median
from time import perf_counter


def measure_execution_time(operation):
    started_at = perf_counter()

    result = operation()

    elapsed = perf_counter() - started_at

    return result, elapsed


def calculate_latency_metrics(latencies):
    values = list(latencies)

    if not values:
        raise ValueError("At least one latency measurement is required.")

    if any(value < 0 for value in values):
        raise ValueError("Latency measurements cannot be negative.")

    ordered = sorted(values)

    p95_index = max(0, int(len(ordered) * 0.95 + 0.999999) - 1)

    return {
        "request_count": len(values),
        "minimum_seconds": min(values),
        "maximum_seconds": max(values),
        "mean_seconds": mean(values),
        "median_seconds": median(values),
        "p95_seconds": ordered[p95_index],
    }
