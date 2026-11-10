import pytest

from app.evaluation.experiments.comparison import compare_experiment
from app.evaluation.experiments.schemas import (
    ExperimentConfig,
    ExperimentObservation,
)


def make_config(**overrides):
    values = {
        "experiment_id": "exp-1",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "metric_name": "accuracy",
        "minimum_samples_per_variant": 10,
        "bootstrap_iterations": 1000,
        "random_seed": 42,
    }

    values.update(overrides)

    return ExperimentConfig(**values)


def make_observations(candidate_values=None):
    if candidate_values is None:
        candidate_values = [0.9] * 20

    baseline_values = [0.7] * len(candidate_values)

    observations = []

    for index, (baseline, candidate) in enumerate(
        zip(baseline_values, candidate_values)
    ):
        sample_id = f"sample-{index}"

        observations.extend([
            ExperimentObservation(
                experiment_id="exp-1",
                variant="baseline",
                metric_name="accuracy",
                sample_id=sample_id,
                value=baseline,
            ),
            ExperimentObservation(
                experiment_id="exp-1",
                variant="candidate",
                metric_name="accuracy",
                sample_id=sample_id,
                value=candidate,
            ),
        ])

    return observations


def test_comparison_calculates_variant_statistics():
    report = compare_experiment(
        make_config(),
        make_observations(),
    )

    assert report.baseline_statistics.mean == pytest.approx(0.7)
    assert report.candidate_statistics.mean == pytest.approx(0.9)
    assert report.paired_sample_count == 20


def test_candidate_wins_for_higher_is_better_metric():
    report = compare_experiment(
        make_config(),
        make_observations(),
    )

    assert report.winner == "candidate"
    assert report.passed is True


def test_lower_is_better_metric():
    config = make_config(
        metric_name="latency",
        higher_is_better=False,
    )

    observations = make_observations(
        candidate_values=[0.5] * 20,
    )

    for item in observations:
        item.metric_name = "latency"

        if item.variant == "baseline":
            item.value = 0.8

    report = compare_experiment(config, observations)

    assert report.winner == "candidate"
    assert report.passed is True


def test_baseline_wins_when_candidate_is_worse():
    report = compare_experiment(
        make_config(),
        make_observations([0.5] * 20),
    )

    assert report.winner == "baseline"
    assert report.passed is False


def test_no_significant_effect_has_no_winner():
    values = [
        0.700, 0.701, 0.699, 0.700, 0.701,
        0.699, 0.700, 0.701, 0.699, 0.700,
        0.701, 0.699, 0.700, 0.701, 0.699,
        0.700, 0.701, 0.699, 0.700, 0.701,
    ]

    report = compare_experiment(
        make_config(),
        make_observations(values),
    )

    assert report.statistically_significant is False
    assert report.winner is None


def test_practical_significance_threshold():
    config = make_config(minimum_effect_size=0.5)

    report = compare_experiment(
        config,
        make_observations(),
    )

    assert report.statistically_significant is True
    assert report.practical_significance is False
    assert report.passed is False


def test_report_contains_confidence_interval():
    report = compare_experiment(
        make_config(),
        make_observations(),
    )

    assert (
        report.confidence_interval_lower
        <= report.confidence_interval_upper
    )


def test_effect_size_is_calculated():
    report = compare_experiment(
        make_config(),
        make_observations(),
    )

    assert report.effect_size > 0


def test_report_contains_violations_when_not_passed():
    report = compare_experiment(
        make_config(minimum_effect_size=0.5),
        make_observations(),
    )

    assert "minimum_practical_effect_not_met" in report.violations
