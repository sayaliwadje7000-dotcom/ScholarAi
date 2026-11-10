import pytest

from app.evaluation.experiments.exceptions import (
    DuplicateExperimentError,
    ExperimentNotFoundError,
)
from app.evaluation.experiments.registry import ExperimentRegistry
from app.evaluation.experiments.schemas import (
    ExperimentConfig,
    ExperimentObservation,
)


def make_config():
    return ExperimentConfig(
        experiment_id="exp-1",
        baseline_variant="baseline",
        candidate_variant="candidate",
        metric_name="accuracy",
    )


def make_observation(variant="baseline", sample_id="s1"):
    return ExperimentObservation(
        experiment_id="exp-1",
        variant=variant,
        metric_name="accuracy",
        sample_id=sample_id,
        value=0.8,
    )


def test_create_experiment():
    registry = ExperimentRegistry()

    record = registry.create(make_config())

    assert record.experiment_id == "exp-1"
    assert record.status == "created"


def test_duplicate_experiment_rejected():
    registry = ExperimentRegistry()
    registry.create(make_config())

    with pytest.raises(DuplicateExperimentError):
        registry.create(make_config())


def test_get_missing_experiment():
    registry = ExperimentRegistry()

    with pytest.raises(ExperimentNotFoundError):
        registry.get("missing")


def test_add_observation():
    registry = ExperimentRegistry()
    registry.create(make_config())

    record = registry.add_observation(
        "exp-1",
        make_observation(),
    )

    assert len(record.observations) == 1


def test_duplicate_observation_rejected():
    registry = ExperimentRegistry()
    registry.create(make_config())

    registry.add_observation("exp-1", make_observation())

    with pytest.raises(ValueError):
        registry.add_observation("exp-1", make_observation())


def test_list_experiments():
    registry = ExperimentRegistry()
    registry.create(make_config())

    assert len(registry.list_all()) == 1


def test_complete_experiment():
    registry = ExperimentRegistry()
    registry.create(make_config())

    record = registry.complete("exp-1")

    assert record.status == "completed"
    assert record.completed_at is not None


def test_completed_experiment_rejects_observations():
    registry = ExperimentRegistry()
    registry.create(make_config())
    registry.complete("exp-1")

    with pytest.raises(ValueError):
        registry.add_observation(
            "exp-1",
            make_observation(),
        )


def test_delete_experiment():
    registry = ExperimentRegistry()
    registry.create(make_config())

    registry.delete("exp-1")

    assert len(registry) == 0


def test_returned_records_are_independent_copies():
    registry = ExperimentRegistry()
    original = registry.create(make_config())

    original.status = "completed"

    assert registry.get("exp-1").status == "created"
