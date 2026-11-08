from datetime import datetime, timezone

from app.services.recommendations.ml.experiments.experiment_record import (
    ExperimentRecord,
)


def make_record():

    now = datetime.now(timezone.utc)

    return ExperimentRecord(
        schema_version="1.0",
        run_id="test-run-001",
        recorded_at=now,
        trained_at=now,
        model_name="logistic_regression",
        training_configuration={
            "random_state": 42,
        },
        training_statistics={
            "total_samples": 100,
        },
        validation_statistics={
            "total_samples": 20,
        },
        training_class_distribution={
            "0": 50,
            "1": 50,
        },
        validation_class_distribution={
            "0": 10,
            "1": 10,
        },
        feature_names=(
            "feature_1",
            "feature_2",
        ),
        evaluation_report={
            "run_id": "test-run-001",
        },
        environment={
            "python_version": "3.12",
        },
        dataset_fingerprint="abc123",
        tags={
            "stage": "baseline",
        },
    )


def test_experiment_record_serialization():

    record = make_record()

    result = record.to_dict()

    assert result["run_id"] == "test-run-001"

    assert result["model_name"] == "logistic_regression"

    assert result["feature_names"] == [
        "feature_1",
        "feature_2",
    ]

    assert result["tags"]["stage"] == "baseline"


def test_experiment_record_serializes_datetime():

    record = make_record()

    result = record.to_dict()

    assert isinstance(
        result["recorded_at"],
        str,
    )

    assert isinstance(
        result["trained_at"],
        str,
    )