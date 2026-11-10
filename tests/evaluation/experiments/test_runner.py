import pytest

from app.evaluation.experiments.exceptions import (
    ExperimentComparisonError,
)
from app.evaluation.experiments.runner import ExperimentRunner
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
        minimum_samples_per_variant=10,
        bootstrap_iterations=500,
    )


def populate_runner(runner):
    runner.create_experiment(make_config())

    for index in range(20):
        sample_id = f"sample-{index}"

        runner.record_observation(
            "exp-1",
            ExperimentObservation(
                experiment_id="exp-1",
                variant="baseline",
                metric_name="accuracy",
                sample_id=sample_id,
                value=0.7,
            ),
        )

        runner.record_observation(
            "exp-1",
            ExperimentObservation(
                experiment_id="exp-1",
                variant="candidate",
                metric_name="accuracy",
                sample_id=sample_id,
                value=0.9,
            ),
        )


def test_runner_creates_experiment():
    runner = ExperimentRunner()

    record = runner.create_experiment(make_config())

    assert record.status == "created"


def test_runner_records_observations():
    runner = ExperimentRunner()
    populate_runner(runner)

    record = runner.get_experiment("exp-1")

    assert len(record.observations) == 40


def test_runner_evaluates_experiment():
    runner = ExperimentRunner()
    populate_runner(runner)

    report = runner.run("exp-1")

    assert report.passed is True
    assert report.winner == "candidate"


def test_runner_completes_experiment():
    runner = ExperimentRunner()
    populate_runner(runner)

    runner.run("exp-1")

    record = runner.get_experiment("exp-1")

    assert record.status == "completed"
    assert record.completed_at is not None


def test_completed_experiment_cannot_run_again():
    runner = ExperimentRunner()
    populate_runner(runner)

    runner.run("exp-1")

    with pytest.raises(ExperimentComparisonError):
        runner.run("exp-1")


def test_invalid_experiment_data_is_wrapped():
    runner = ExperimentRunner()
    runner.create_experiment(make_config())

    with pytest.raises(ExperimentComparisonError):
        runner.run("exp-1")


def test_runner_lists_experiments():
    runner = ExperimentRunner()
    populate_runner(runner)

    assert len(runner.list_experiments()) == 1
