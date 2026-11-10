import pytest
from pydantic import ValidationError

from app.evaluation.experiments.schemas import (
    ExperimentConfig,
    ExperimentObservation,
    ExperimentRecord,
)


def make_config(**overrides):
    values = {
        "experiment_id": "experiment-1",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "metric_name": "accuracy",
    }
    values.update(overrides)
    return ExperimentConfig(**values)


def test_experiment_config_creation():
    config = make_config()

    assert config.experiment_id == "experiment-1"
    assert config.alpha == 0.05
    assert config.minimum_samples_per_variant == 10


def test_experiment_rejects_identical_variants():
    with pytest.raises(ValidationError):
        make_config(candidate_variant="baseline")


def test_experiment_rejects_invalid_alpha():
    with pytest.raises(ValidationError):
        make_config(alpha=1.5)


def test_experiment_rejects_invalid_sample_count():
    with pytest.raises(ValidationError):
        make_config(minimum_samples_per_variant=1)


def test_observation_creation():
    observation = ExperimentObservation(
        experiment_id="experiment-1",
        variant="baseline",
        metric_name="accuracy",
        sample_id="sample-1",
        value=0.85,
    )

    assert observation.value == 0.85
    assert observation.metadata == {}


def test_observation_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ExperimentObservation(
            experiment_id="experiment-1",
            variant="baseline",
            metric_name="accuracy",
            sample_id="sample-1",
            value=0.85,
            unknown_field="invalid",
        )


def test_record_requires_matching_experiment_id():
    config = make_config()

    with pytest.raises(ValidationError):
        ExperimentRecord(
            experiment_id="different-id",
            config=config,
        )
