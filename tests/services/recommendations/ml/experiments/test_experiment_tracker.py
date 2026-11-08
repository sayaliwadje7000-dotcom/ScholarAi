from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pytest

from app.services.recommendations.ml.experiments.experiment_config import (
    ExperimentTrackingConfig,
)

from app.services.recommendations.ml.experiments.experiment_tracker import (
    DuplicateExperimentRunError,
    ExperimentNotFoundError,
    ExperimentStorageError,
    InvalidExperimentRunError,
    RecommendationExperimentTracker,
)


@dataclass(frozen=True)
class FakeStatistics:

    total_samples: int

    relevant_samples: int

    not_relevant_samples: int

    unique_users: int

    unique_resources: int


@dataclass(frozen=True)
class FakeTrainingConfig:

    random_state: int = 42

    validation_size: float = 0.2


class FakeEvaluationReport:

    def __init__(self, run_id):

        self.run_id = run_id

    def to_dict(self):

        return {
            "run_id": self.run_id,
            "trained_model": {
                "classification": {
                    "accuracy": 0.9,
                    "precision": 0.9,
                    "recall": 0.9,
                    "f1_score": 0.9,
                    "roc_auc": 0.95,
                    "average_precision": 0.94,
                },
                "ranking": {
                    "precision_at_5": 0.8,
                    "recall_at_5": 0.7,
                    "ndcg_at_5": 0.85,
                },
            },
        }


def make_training_result():

    run_id = "test-run-001"

    statistics = FakeStatistics(
        total_samples=100,
        relevant_samples=50,
        not_relevant_samples=50,
        unique_users=20,
        unique_resources=80,
    )

    evaluation_dataset = SimpleNamespace(
        X=np.zeros((20, 3)),
        y=np.asarray(
            [0, 1] * 10,
            dtype=np.int64,
        ),
        user_ids=tuple(
            f"user-{index}"
            for index in range(20)
        ),
        resource_ids=tuple(
            f"resource-{index}"
            for index in range(20)
        ),
    )

    return SimpleNamespace(
        run_id=run_id,
        trained_at=datetime.now(timezone.utc),
        model=SimpleNamespace(
            model_name="logistic_regression"
        ),
        config=FakeTrainingConfig(),
        training_statistics=statistics,
        validation_statistics=statistics,
        training_class_distribution={
            0: 50,
            1: 50,
        },
        validation_class_distribution={
            0: 10,
            1: 10,
        },
        feature_names=(
            "feature_1",
            "feature_2",
            "feature_3",
        ),
        evaluation_dataset=evaluation_dataset,
    )


def make_tracker(tmp_path):

    config = ExperimentTrackingConfig(
        storage_directory=tmp_path / "experiments"
    )

    return RecommendationExperimentTracker(
        config=config
    )


def test_tracker_initializes_storage(tmp_path):

    tracker = make_tracker(tmp_path)

    assert tracker.storage_directory.exists()

    assert tracker.storage_directory.is_dir()


def test_tracker_records_experiment(tmp_path):

    tracker = make_tracker(tmp_path)

    training_result = make_training_result()

    report = FakeEvaluationReport(
        training_result.run_id
    )

    record = tracker.record_run(
        training_result=training_result,
        evaluation_report=report,
        tags={
            "stage": "baseline",
            "phase": "14.7",
        },
    )

    assert record.run_id == "test-run-001"

    assert record.model_name == "logistic_regression"

    assert record.training_configuration["random_state"] == 42

    assert record.dataset_fingerprint is not None

    assert len(record.dataset_fingerprint) == 64

    assert record.tags["phase"] == "14.7"


def test_tracker_persists_json_file(tmp_path):

    tracker = make_tracker(tmp_path)

    training_result = make_training_result()

    tracker.record_run(
        training_result,
        FakeEvaluationReport(
            training_result.run_id
        ),
    )

    path = (
        tracker.storage_directory
        / "test-run-001.json"
    )

    assert path.exists()

    loaded = tracker.get_run(
        "test-run-001"
    )

    assert loaded["run_id"] == "test-run-001"


def test_tracker_lists_experiments(tmp_path):

    tracker = make_tracker(tmp_path)

    training_result = make_training_result()

    tracker.record_run(
        training_result,
        FakeEvaluationReport(
            training_result.run_id
        ),
    )

    records = tracker.list_runs()

    assert len(records) == 1

    assert records[0]["run_id"] == "test-run-001"


def test_tracker_rejects_duplicate_run(tmp_path):

    tracker = make_tracker(tmp_path)

    training_result = make_training_result()

    report = FakeEvaluationReport(
        training_result.run_id
    )

    tracker.record_run(
        training_result,
        report,
    )

    with pytest.raises(DuplicateExperimentRunError):

        tracker.record_run(
            training_result,
            report,
        )


def test_tracker_rejects_invalid_run_id(tmp_path):

    tracker = make_tracker(tmp_path)

    training_result = make_training_result()

    training_result.run_id = "../outside"

    with pytest.raises(InvalidExperimentRunError):

        tracker.record_run(
            training_result,
            FakeEvaluationReport("../outside"),
        )


def test_tracker_rejects_mismatched_evaluation_run(
    tmp_path,
):

    tracker = make_tracker(tmp_path)

    training_result = make_training_result()

    report = FakeEvaluationReport(
        "different-run"
    )

    with pytest.raises(InvalidExperimentRunError):

        tracker.record_run(
            training_result,
            report,
        )


def test_tracker_retrieves_missing_run_error(tmp_path):

    tracker = make_tracker(tmp_path)

    with pytest.raises(ExperimentNotFoundError):

        tracker.get_run(
            "missing-run"
        )


def test_tracker_excludes_user_and_resource_ids(
    tmp_path,
):

    tracker = make_tracker(tmp_path)

    training_result = make_training_result()

    tracker.record_run(
        training_result,
        FakeEvaluationReport(
            training_result.run_id
        ),
    )

    loaded = tracker.get_run(
        "test-run-001"
    )

    serialized = str(loaded)

    assert "user-0" not in serialized

    assert "resource-0" not in serialized


def test_tracker_rejects_invalid_tags(tmp_path):

    tracker = make_tracker(tmp_path)

    training_result = make_training_result()

    with pytest.raises(InvalidExperimentRunError):

        tracker.record_run(
            training_result,
            FakeEvaluationReport(
                training_result.run_id
            ),
            tags={
                "stage": "",
            },
        )


def test_dataset_fingerprint_is_deterministic(tmp_path):

    tracker = make_tracker(tmp_path)

    first = make_training_result()

    second = make_training_result()

    second.evaluation_dataset = first.evaluation_dataset

    first_record = tracker._build_record(
        first,
        FakeEvaluationReport(first.run_id),
        {},
        None,
    )

    second.run_id = "test-run-002"

    second_record = tracker._build_record(
        second,
        FakeEvaluationReport(second.run_id),
        {},
        None,
    )

    assert (
        first_record.dataset_fingerprint
        == second_record.dataset_fingerprint
    )