import pytest

from app.evaluation.experiments.exceptions import (
    ExperimentValidationError,
)
from app.evaluation.experiments.statistics import (
    bootstrap_mean_difference,
    confidence_interval,
    mean,
    median,
    normal_two_sided_p_value,
    paired_effect_size,
    percentile,
    standard_deviation,
    standard_error,
    variance,
)


def test_mean():
    assert mean([1, 2, 3, 4]) == 2.5


def test_median_odd():
    assert median([1, 3, 2]) == 2


def test_median_even():
    assert median([1, 2, 3, 4]) == 2.5


def test_sample_variance():
    assert variance([1, 2, 3]) == 1


def test_population_variance():
    assert variance([1, 2, 3], sample=False) == pytest.approx(2 / 3)


def test_standard_deviation():
    assert standard_deviation([1, 2, 3]) == 1


def test_standard_error():
    assert standard_error([1, 2, 3]) == pytest.approx(1 / 3 ** 0.5)


def test_percentile_interpolation():
    assert percentile([1, 2, 3, 4], 50) == 2.5


def test_percentile_rejects_invalid_value():
    with pytest.raises(ExperimentValidationError):
        percentile([1, 2], 110)


def test_confidence_interval():
    lower, upper = confidence_interval([10, 11, 12, 13, 14])

    assert lower < mean([10, 11, 12, 13, 14])
    assert upper > mean([10, 11, 12, 13, 14])


def test_confidence_interval_rejects_single_value():
    with pytest.raises(ExperimentValidationError):
        confidence_interval([10])


def test_bootstrap_is_reproducible():
    first = bootstrap_mean_difference(
        [1, 2, 3, 4, 5],
        iterations=500,
        random_seed=42,
    )

    second = bootstrap_mean_difference(
        [1, 2, 3, 4, 5],
        iterations=500,
        random_seed=42,
    )

    assert first == second


def test_bootstrap_interval_contains_mean():
    values = [2, 3, 4, 5, 6]

    lower, upper = bootstrap_mean_difference(
        values,
        iterations=1000,
    )

    assert lower <= mean(values) <= upper


def test_normal_p_value_for_zero_effect():
    assert normal_two_sided_p_value(0, 1) == 1


def test_normal_p_value_for_large_effect():
    assert normal_two_sided_p_value(10, 1) < 0.001


def test_paired_effect_size():
    assert paired_effect_size([1, 2, 3]) > 0


def test_effect_size_zero_variance():
    assert paired_effect_size([2, 2, 2]) == float("inf")


def test_empty_values_are_rejected():
    with pytest.raises(ExperimentValidationError):
        mean([])


def test_non_finite_values_are_rejected():
    with pytest.raises(ExperimentValidationError):
        mean([1, float("nan")])


def test_sample_variance_requires_two_values():
    with pytest.raises(ExperimentValidationError):
        variance([1])
