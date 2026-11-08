import pytest

from app.services.recommendations.ml.experiments.experiment_comparison import (
    ExperimentComparisonError,
    compare_experiments,
)


def make_experiment(
    run_id,
    accuracy,
    f1_score,
    ndcg,
):

    return {
        "run_id": run_id,

        "model_name": "logistic_regression",

        "evaluation_report": {
            "trained_model": {
                "classification": {
                    "accuracy": accuracy,
                    "precision": 0.8,
                    "recall": 0.7,
                    "f1_score": f1_score,
                    "roc_auc": 0.9,
                    "average_precision": 0.88,
                },

                "ranking": {
                    "ndcg_at_5": ndcg,
                },
            }
        },
    }


def test_compare_experiments():

    records = [
        make_experiment(
            "run-001",
            0.80,
            0.78,
            0.72,
        ),
        make_experiment(
            "run-002",
            0.90,
            0.88,
            0.85,
        ),
    ]

    results = compare_experiments(records)

    assert len(results) == 2

    assert results[0].run_id == "run-001"

    assert results[1].run_id == "run-002"

    assert results[1].accuracy == 0.90

    assert results[1].f1_score == 0.88

    assert results[1].ranking_metrics["ndcg_at_5"] == 0.85


def test_comparison_serialization():

    results = compare_experiments(
        [
            make_experiment(
                "run-001",
                0.9,
                0.8,
                0.7,
            )
        ]
    )

    result = results[0].to_dict()

    assert result["run_id"] == "run-001"

    assert result["accuracy"] == 0.9


def test_comparison_rejects_empty_records():

    with pytest.raises(ExperimentComparisonError):

        compare_experiments([])


def test_comparison_rejects_duplicate_run_ids():

    record = make_experiment(
        "run-001",
        0.9,
        0.8,
        0.7,
    )

    with pytest.raises(ExperimentComparisonError):

        compare_experiments(
            [
                record,
                record,
            ]
        )


def test_comparison_handles_missing_metrics():

    record = {
        "run_id": "run-001",
        "model_name": "baseline",
        "evaluation_report": {
            "trained_model": {
                "classification": {},
                "ranking": {},
            }
        },
    }

    result = compare_experiments(
        [record]
    )[0]

    assert result.accuracy is None

    assert result.f1_score is None

    assert result.ranking_metrics == {}


def test_comparison_rejects_non_finite_metrics():

    record = make_experiment(
        "run-001",
        float("nan"),
        0.8,
        0.7,
    )

    with pytest.raises(ExperimentComparisonError):

        compare_experiments(
            [record]
        )