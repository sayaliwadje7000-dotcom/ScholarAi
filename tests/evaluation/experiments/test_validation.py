import pytest

from app.evaluation.experiments.exceptions import (
    ExperimentValidationError,
)
from app.evaluation.experiments.schemas import (
    ExperimentConfig,
    ExperimentObservation,
)
from app.evaluation.experiments.validation import validate_observations


def make_config():
    return ExperimentConfig(
        experiment_id="exp-1",
        baseline_variant="baseline",
        candidate_variant="candidate",
        metric_name="accuracy",
        minimum_samples_per_variant=2,
    )


def make_observations():
    result = []

    for sample_id in ["s1", "s2"]:
        result.append(
            ExperimentObservation(
                experiment_id="exp-1",
                variant="baseline",
                metric_name="accuracy",
                sample_id=sample_id,
                value=0.7,
            )
        )

        result.append(
            ExperimentObservation(
                experiment_id="exp-1",
                variant="candidate",
                metric_name="accuracy",
                sample_id=sample_id,
                value=0.8,
            )
        )

    return result


def test_valid_observations_are_grouped():
    grouped = validate_observations(
        make_config(),
        make_observations(),
    )

    assert len(grouped["baseline"]) == 2
    assert len(grouped["candidate"]) == 2


def test_empty_observations_rejected():
    with pytest.raises(ExperimentValidationError):
        validate_observations(make_config(), [])


def test_wrong_experiment_id_rejected():
    observations = make_observations()
    observations[0].experiment_id = "other"

    with pytest.raises(ExperimentValidationError):
        validate_observations(make_config(), observations)


def test_wrong_metric_rejected():
    observations = make_observations()
    observations[0].metric_name = "latency"

    with pytest.raises(ExperimentValidationError):
        validate_observations(make_config(), observations)


def test_unknown_variant_rejected():
    observations = make_observations()
    observations[0].variant = "unknown"

    with pytest.raises(ExperimentValidationError):
        validate_observations(make_config(), observations)


def test_duplicate_sample_variant_rejected():
    observations = make_observations()
    observations.append(observations[0].model_copy(deep=True))

    with pytest.raises(ExperimentValidationError):
        validate_observations(make_config(), observations)


def test_insufficient_baseline_samples_rejected():
    observations = make_observations()
    observations = [
        item
        for item in observations
        if not (
            item.variant == "baseline"
            and item.sample_id == "s2"
        )
    ]

    with pytest.raises(ExperimentValidationError):
        validate_observations(make_config(), observations)


def test_unpaired_samples_rejected():
    observations = make_observations()
    observations[-1].sample_id = "different"

    with pytest.raises(ExperimentValidationError):
        validate_observations(make_config(), observations)
