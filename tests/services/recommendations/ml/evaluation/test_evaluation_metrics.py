import numpy as np

from app.services.recommendations.ml.evaluation.evaluation_config import (
    EvaluationConfig,
)

from app.services.recommendations.ml.evaluation.evaluation_service import (
    RecommendationModelEvaluator,
)


def test_classification_metrics():

    evaluator = RecommendationModelEvaluator()

    labels = np.asarray(
        [0, 0, 1, 1],
        dtype=np.int64,
    )

    probabilities = np.asarray(
        [0.10, 0.20, 0.80, 0.90],
        dtype=np.float64,
    )

    metrics = evaluator._classification_metrics(
        labels,
        probabilities,
    )

    assert metrics.accuracy == 1.0

    assert metrics.precision == 1.0

    assert metrics.recall == 1.0

    assert metrics.f1_score == 1.0

    assert metrics.roc_auc == 1.0

    assert metrics.pr_auc == 1.0

    assert metrics.average_precision == 1.0

    assert metrics.confusion_matrix == (
        (2, 0),
        (0, 2),
    )


def test_class_imbalance_calculation():

    evaluator = RecommendationModelEvaluator()

    labels = np.asarray(
        [0, 0, 0, 0, 0, 0, 1, 1],
        dtype=np.int64,
    )

    distribution = evaluator._class_distribution(
        labels,
    )

    assert distribution.total_samples == 8

    assert distribution.relevant_samples == 2

    assert distribution.not_relevant_samples == 6

    assert distribution.imbalance_ratio == 3.0


def test_balanced_class_distribution():

    evaluator = RecommendationModelEvaluator()

    labels = np.asarray(
        [0, 0, 1, 1],
        dtype=np.int64,
    )

    distribution = evaluator._class_distribution(
        labels,
    )

    assert distribution.imbalance_ratio == 1.0


def test_ranking_metrics():

    evaluator = RecommendationModelEvaluator(
        EvaluationConfig(
            ranking_k_values=(1, 2),
        )
    )

    labels = np.asarray(
        [1, 0, 1, 0],
        dtype=np.int64,
    )

    probabilities = np.asarray(
        [0.95, 0.80, 0.70, 0.10],
        dtype=np.float64,
    )

    users = (
        "user-a",
        "user-a",
        "user-b",
        "user-b",
    )

    resources = (
        "resource-a",
        "resource-b",
        "resource-c",
        "resource-d",
    )

    metrics = evaluator._ranking_metrics(
        labels=labels,
        probabilities=probabilities,
        user_ids=users,
        resource_ids=resources,
    )

    assert metrics.evaluated_users == 2

    assert metrics.precision_at_k[1] == 1.0

    assert metrics.recall_at_k[1] == 1.0

    assert metrics.ndcg_at_k[1] == 1.0


def test_ranking_tie_breaking_is_deterministic():

    evaluator = RecommendationModelEvaluator(
        EvaluationConfig(
            ranking_k_values=(1,),
        )
    )

    labels = np.asarray(
        [1, 0],
        dtype=np.int64,
    )

    probabilities = np.asarray(
        [0.5, 0.5],
        dtype=np.float64,
    )

    metrics = evaluator._ranking_metrics(
        labels=labels,
        probabilities=probabilities,
        user_ids=("user-a", "user-a"),
        resource_ids=("resource-a", "resource-b"),
    )

    assert metrics.precision_at_k[1] == 1.0