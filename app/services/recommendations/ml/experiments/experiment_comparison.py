"""Comparison utilities for stored recommendation experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


class ExperimentComparisonError(Exception):
    """Raised when experiment comparison cannot be completed."""


@dataclass(frozen=True, slots=True)
class ExperimentComparison:
    """Comparison of selected metrics across experiment runs."""

    run_id: str

    model_name: str

    accuracy: float | None

    precision: float | None

    recall: float | None

    f1_score: float | None

    roc_auc: float | None

    average_precision: float | None

    ranking_metrics: dict[str, float]

    def to_dict(self) -> dict[str, Any]:

        return {
            "run_id": self.run_id,

            "model_name": self.model_name,

            "accuracy": self.accuracy,

            "precision": self.precision,

            "recall": self.recall,

            "f1_score": self.f1_score,

            "roc_auc": self.roc_auc,

            "average_precision": self.average_precision,

            "ranking_metrics": self.ranking_metrics,
        }


def _optional_float(
    value: Any,
    metric_name: str,
) -> float | None:

    if value is None:
        return None

    if isinstance(value, bool):

        raise ExperimentComparisonError(
            f"Invalid boolean value for metric {metric_name}."
        )

    try:

        result = float(value)

    except (TypeError, ValueError) as exc:

        raise ExperimentComparisonError(
            f"Invalid numeric value for metric {metric_name}."
        ) from exc

    import math

    if not math.isfinite(result):

        raise ExperimentComparisonError(
            f"Metric {metric_name} must be finite."
        )

    return result


def _extract_metric(
    metrics: dict[str, Any],
    name: str,
) -> float | None:

    return _optional_float(
        metrics.get(name),
        name,
    )


def compare_experiments(
    experiment_records: Sequence[dict[str, Any]],
) -> list[ExperimentComparison]:
    """
    Extract comparable metrics from experiment records.

    Expected evaluation report structure:

        evaluation_report:
            trained_model:
                classification:
                    accuracy
                    precision
                    recall
                    f1_score
                    roc_auc
                    average_precision

                ranking:
                    precision_at_k
                    recall_at_k
                    ndcg_at_k
    """

    if not experiment_records:

        raise ExperimentComparisonError(
            "At least one experiment is required."
        )

    comparisons = []

    seen_run_ids = set()

    for record in experiment_records:

        if not isinstance(record, dict):

            raise ExperimentComparisonError(
                "Experiment records must be dictionaries."
            )

        run_id = record.get("run_id")

        if not isinstance(run_id, str) or not run_id:

            raise ExperimentComparisonError(
                "Experiment record has no valid run ID."
            )

        if run_id in seen_run_ids:

            raise ExperimentComparisonError(
                f"Duplicate experiment run ID: {run_id}"
            )

        seen_run_ids.add(run_id)

        evaluation = record.get(
            "evaluation_report",
            {},
        )

        if not isinstance(evaluation, dict):

            raise ExperimentComparisonError(
                f"Invalid evaluation report for run {run_id}."
            )

        trained_model = evaluation.get(
            "trained_model",
            {},
        )

        if not isinstance(trained_model, dict):

            raise ExperimentComparisonError(
                f"Invalid trained-model report for run {run_id}."
            )

        classification = trained_model.get(
            "classification",
            {},
        )

        ranking = trained_model.get(
            "ranking",
            {},
        )

        if not isinstance(classification, dict):
            classification = {}

        if not isinstance(ranking, dict):
            ranking = {}

        ranking_metrics = {}

        for name, value in ranking.items():

            metric_value = _optional_float(
                value,
                name,
            )

            if metric_value is not None:

                ranking_metrics[name] = metric_value

        comparisons.append(
            ExperimentComparison(
                run_id=run_id,

                model_name=str(
                    record.get(
                        "model_name",
                        "unknown",
                    )
                ),

                accuracy=_extract_metric(
                    classification,
                    "accuracy",
                ),

                precision=_extract_metric(
                    classification,
                    "precision",
                ),

                recall=_extract_metric(
                    classification,
                    "recall",
                ),

                f1_score=_extract_metric(
                    classification,
                    "f1_score",
                ),

                roc_auc=_extract_metric(
                    classification,
                    "roc_auc",
                ),

                average_precision=_extract_metric(
                    classification,
                    "average_precision",
                ),

                ranking_metrics=ranking_metrics,
            )
        )

    return comparisons