import pytest

from app.evaluation.optimization.exceptions import (
    OptimizationValidationError,
)
from app.evaluation.optimization.results import (
    summarize_metrics,
    validate_metric_values,
)


def test_validate_metric_values():
    validate_metric_values(
        {"quality": [0.8, 0.9]},
        minimum_samples=2,
    )


def test_reject_empty_metrics():
    with pytest.raises(OptimizationValidationError):
        validate_metric_values({}, minimum_samples=1)


def test_reject_insufficient_samples():
    with pytest.raises(OptimizationValidationError):
        validate_metric_values(
            {"quality": [0.8]},
            minimum_samples=2,
        )


def test_reject_non_finite_values():
    with pytest.raises(OptimizationValidationError):
        validate_metric_values(
            {"quality": [0.8, float("nan")]},
            minimum_samples=2,
        )


def test_summarize_metrics():
    means, deviations, counts = summarize_metrics(
        {"quality": [0.8, 1.0]}
    )

    assert means["quality"] == pytest.approx(0.9)
    assert deviations["quality"] == pytest.approx(0.1414213562)
    assert counts["quality"] == 2


def test_single_sample_standard_deviation():
    _, deviations, counts = summarize_metrics(
        {"quality": [0.8]}
    )

    assert deviations["quality"] == 0.0
    assert counts["quality"] == 1
