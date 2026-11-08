from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import numpy as np
import pytest

from app.services.recommendations.ml.evaluation.evaluation_service import (
    EvaluationInputError,
    EvaluationPredictionError,
    RecommendationModelEvaluator,
)

from app.services.recommendations.ml.training.training_config import (
    TrainingConfig,
)

from app.services.recommendations.ml.training.training_pipeline import (
    DatasetStatistics,
    EvaluationDataset,
    TrainingResult,
)


class FakeModel:

    def __init__(self, probabilities):
        self.probabilities = np.asarray(
            probabilities,
            dtype=np.float64,
        )

    def predict_proba(self, features):
        return self.probabilities


def make_training_result(
    model=None,
    evaluation_dataset=None,
):
    # Four training users.
    training_user_ids = tuple(
        uuid4()
        for _ in range(4)
    )

    # Four separate validation users.
    validation_user_ids = tuple(
        uuid4()
        for _ in range(4)
    )

    # Each validation user has two candidate resources.
    evaluation_user_ids = tuple(
        user_id
        for user_id in validation_user_ids
        for _ in range(2)
    )

    resource_ids = tuple(
        uuid4()
        for _ in range(8)
    )

    X = np.asarray(
        [
            [0.1, 0.2],
            [0.2, 0.3],
            [0.3, 0.4],
            [0.4, 0.5],
            [0.5, 0.6],
            [0.6, 0.7],
            [0.7, 0.8],
            [0.8, 0.9],
        ],
        dtype=np.float64,
    )

    # Each user has:
    # First resource: not relevant
    # Second resource: relevant
    y = np.asarray(
        [0, 1, 0, 1, 0, 1, 0, 1],
        dtype=np.int64,
    )

    training_statistics = DatasetStatistics(
        total_samples=10,
        relevant_samples=5,
        not_relevant_samples=5,
        unique_users=4,
        unique_resources=10,
    )

    validation_statistics = DatasetStatistics(
        total_samples=8,
        relevant_samples=4,
        not_relevant_samples=4,
        unique_users=4,
        unique_resources=8,
    )

    if evaluation_dataset is None:
        evaluation_dataset = EvaluationDataset(
            X=X,
            y=y,
            user_ids=evaluation_user_ids,
            resource_ids=resource_ids,
            statistics=validation_statistics,
        )

    if model is None:
        model = FakeModel(
            [
                [0.9, 0.1],
                [0.1, 0.9],

                [0.8, 0.2],
                [0.2, 0.8],

                [0.7, 0.3],
                [0.3, 0.7],

                [0.6, 0.4],
                [0.4, 0.6],
            ]
        )

    dummy_model = FakeModel(
        [
            [0.5, 0.5],
            [0.5, 0.5],
            [0.5, 0.5],
            [0.5, 0.5],
            [0.5, 0.5],
            [0.5, 0.5],
            [0.5, 0.5],
            [0.5, 0.5],
        ]
    )

    return TrainingResult(
        run_id="test-training-run",
        trained_at=datetime.now(timezone.utc),
        model=model,
        dummy_baseline=dummy_model,
        feature_transformer=None,
        training_summary=None,
        training_statistics=training_statistics,
        validation_statistics=validation_statistics,
        feature_names=(
            "feature_1",
            "feature_2",
        ),
        training_class_distribution={
            0: 5,
            1: 5,
        },
        validation_class_distribution={
            0: 4,
            1: 4,
        },
        training_user_ids=training_user_ids,
        validation_user_ids=validation_user_ids,
        evaluation_dataset=evaluation_dataset,
        config=TrainingConfig(),
    )


def test_evaluator_compares_model_and_dummy():

    evaluator = RecommendationModelEvaluator()

    report = evaluator.evaluate(
        make_training_result()
    )

    assert report.run_id == "test-training-run"

    assert report.trained_model.model_name == (
        "logistic_regression"
    )

    assert report.dummy_baseline.model_name == (
        "dummy_classifier"
    )

    assert report.trained_model.classification.accuracy == 1.0

    assert report.trained_model.classification.f1_score == 1.0

    assert report.trained_model.classification.roc_auc == 1.0

    assert report.trained_model.ranking.evaluated_users == 4

    assert isinstance(
        report.model_outperforms_dummy,
        bool,
    )


def test_evaluation_report_is_serializable():

    evaluator = RecommendationModelEvaluator()

    report = evaluator.evaluate(
        make_training_result()
    )

    result = report.to_dict()

    assert result["run_id"] == "test-training-run"

    assert "trained_model" in result

    assert "dummy_baseline" in result

    assert "comparisons" in result

    assert "notes" in result


def test_evaluator_rejects_empty_validation_data():

    evaluator = RecommendationModelEvaluator()

    original = make_training_result()

    empty_dataset = EvaluationDataset(
        X=np.empty((0, 2), dtype=np.float64),
        y=np.asarray([], dtype=np.int64),
        user_ids=(),
        resource_ids=(),
        statistics=DatasetStatistics(
            total_samples=0,
            relevant_samples=0,
            not_relevant_samples=0,
            unique_users=0,
            unique_resources=0,
        ),
    )

    result = replace(
        original,
        evaluation_dataset=empty_dataset,
    )

    with pytest.raises(EvaluationInputError):
        evaluator.evaluate(result)


def test_evaluator_rejects_mismatched_user_ids():

    evaluator = RecommendationModelEvaluator()

    original = make_training_result()

    malformed_dataset = EvaluationDataset(
        X=np.zeros((8, 2), dtype=np.float64),
        y=np.asarray(
            [0, 1, 0, 1, 0, 1, 0, 1],
            dtype=np.int64,
        ),
        user_ids=("user-a",),
        resource_ids=tuple(
            uuid4()
            for _ in range(8)
        ),
        statistics=DatasetStatistics(
            total_samples=8,
            relevant_samples=4,
            not_relevant_samples=4,
            unique_users=1,
            unique_resources=8,
        ),
    )

    result = replace(
        original,
        evaluation_dataset=malformed_dataset,
    )

    with pytest.raises(EvaluationInputError):
        evaluator.evaluate(result)


def test_evaluator_rejects_invalid_probabilities():

    evaluator = RecommendationModelEvaluator()

    result = make_training_result(
        model=FakeModel(
            [
                [0.9, 0.9],
                [0.1, 0.9],
                [0.8, 0.2],
                [0.2, 0.8],
                [0.7, 0.3],
                [0.3, 0.7],
                [0.6, 0.4],
                [0.4, 0.6],
            ]
        )
    )

    with pytest.raises(EvaluationPredictionError):
        evaluator.evaluate(result)


def test_evaluator_rejects_non_finite_probabilities():

    evaluator = RecommendationModelEvaluator()

    result = make_training_result(
        model=FakeModel(
            [
                [0.9, 0.1],
                [0.1, 0.9],
                [0.8, 0.2],
                [0.2, 0.8],
                [0.7, 0.3],
                [0.3, 0.7],
                [np.nan, 0.6],
                [0.4, 0.6],
            ]
        )
    )

    with pytest.raises(EvaluationPredictionError):
        evaluator.evaluate(result)


def test_evaluator_requires_probability_interface():

    evaluator = RecommendationModelEvaluator()

    result = make_training_result(
        model=Mock(spec=[])
    )

    with pytest.raises(EvaluationPredictionError):
        evaluator.evaluate(result)