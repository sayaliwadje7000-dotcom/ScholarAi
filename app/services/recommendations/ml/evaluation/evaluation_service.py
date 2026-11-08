"""Evaluation service for ScholarAI recommendation models."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

import numpy as np

from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    auc,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    ndcg_score,
)

from app.services.recommendations.ml.evaluation.evaluation_config import (
    EvaluationConfig,
)

from app.services.recommendations.ml.evaluation.evaluation_metrics import (
    ClassificationMetrics,
    ClassDistribution,
    EvaluationReport,
    MetricComparison,
    ModelEvaluation,
    RankingMetrics,
)

from app.services.recommendations.ml.training.training_pipeline import (
    TrainingResult,
)


class ModelEvaluationError(Exception):
    """Base exception for evaluation failures."""


class EvaluationInputError(ModelEvaluationError):
    """Raised when evaluation inputs are invalid."""


class EvaluationPredictionError(ModelEvaluationError):
    """Raised when a model produces invalid predictions."""


@dataclass(frozen=True, slots=True)
class _ValidatedEvaluationData:
    """Validated arrays used internally during evaluation."""

    labels: np.ndarray

    user_ids: tuple

    resource_ids: tuple

    sample_count: int


class RecommendationModelEvaluator:
    """
    Evaluates trained recommendation models.

    Responsibilities:
    - Classification evaluation.
    - Probability evaluation.
    - User-grouped ranking evaluation.
    - Class imbalance analysis.
    - Dummy baseline comparison.

    The evaluator never fits or modifies a model.
    """

    def __init__(
        self,
        config: EvaluationConfig | None = None,
    ) -> None:

        self.config = config or EvaluationConfig()

    # ---------------------------------------------------------
    # Input validation
    # ---------------------------------------------------------

    def _validate_evaluation_data(
        self,
        training_result: TrainingResult,
    ) -> _ValidatedEvaluationData:

        if not isinstance(training_result, TrainingResult):
            raise EvaluationInputError(
                "Expected a TrainingResult instance."
            )

        dataset = training_result.evaluation_dataset

        labels = np.asarray(
            dataset.y,
            dtype=np.int64,
        ).reshape(-1)

        user_ids = tuple(dataset.user_ids)

        resource_ids = tuple(dataset.resource_ids)

        sample_count = len(labels)

        if sample_count == 0:
            raise EvaluationInputError(
                "Validation dataset cannot be empty."
            )

        if len(user_ids) != sample_count:
            raise EvaluationInputError(
                "User identifiers do not match validation labels."
            )

        if len(resource_ids) != sample_count:
            raise EvaluationInputError(
                "Resource identifiers do not match validation labels."
            )

        if not np.isin(labels, [0, 1]).all():
            raise EvaluationInputError(
                "Validation labels must contain only 0 and 1."
            )

        if len(np.unique(labels)) != 2:
            raise EvaluationInputError(
                "Validation data must contain both relevance classes."
            )

        if any(value is None for value in user_ids):
            raise EvaluationInputError(
                "User identifiers cannot contain None."
            )

        if any(value is None for value in resource_ids):
            raise EvaluationInputError(
                "Resource identifiers cannot contain None."
            )

        pairs = list(zip(user_ids, resource_ids))

        if len(set(pairs)) != sample_count:
            raise EvaluationInputError(
                "Duplicate user-resource evaluation pairs detected."
            )

        return _ValidatedEvaluationData(
            labels=labels,
            user_ids=user_ids,
            resource_ids=resource_ids,
            sample_count=sample_count,
        )

    # ---------------------------------------------------------
    # Prediction validation
    # ---------------------------------------------------------

    @staticmethod
    def _get_positive_probabilities(
        model,
        features,
        sample_count: int,
    ) -> np.ndarray:

        if not hasattr(model, "predict_proba"):
            raise EvaluationPredictionError(
                "Model does not expose predict_proba()."
            )

        try:
            probabilities = np.asarray(
                model.predict_proba(features),
                dtype=np.float64,
            )

        except Exception as exc:
            raise EvaluationPredictionError(
                "Model probability prediction failed."
            ) from exc

        if probabilities.ndim != 2:
            raise EvaluationPredictionError(
                "Expected a two-dimensional probability matrix."
            )

        if probabilities.shape != (sample_count, 2):
            raise EvaluationPredictionError(
                "Expected probability matrix with shape "
                f"({sample_count}, 2)."
            )

        if not np.isfinite(probabilities).all():
            raise EvaluationPredictionError(
                "Predicted probabilities contain non-finite values."
            )

        if np.any(probabilities < 0.0) or np.any(probabilities > 1.0):
            raise EvaluationPredictionError(
                "Predicted probabilities must be between 0 and 1."
            )

        if not np.allclose(
            probabilities.sum(axis=1),
            1.0,
            atol=1e-6,
        ):
            raise EvaluationPredictionError(
                "Predicted class probabilities must sum to 1."
            )

        return probabilities[:, 1]

    # ---------------------------------------------------------
    # Classification metrics
    # ---------------------------------------------------------

    def _classification_metrics(
        self,
        labels: np.ndarray,
        probabilities: np.ndarray,
    ) -> ClassificationMetrics:

        predictions = (
            probabilities >= self.config.classification_threshold
        ).astype(np.int64)

        accuracy = accuracy_score(
            labels,
            predictions,
        )

        precision = precision_score(
            labels,
            predictions,
            pos_label=self.config.positive_label,
            zero_division=0,
        )

        recall = recall_score(
            labels,
            predictions,
            pos_label=self.config.positive_label,
            zero_division=0,
        )

        f1 = f1_score(
            labels,
            predictions,
            pos_label=self.config.positive_label,
            zero_division=0,
        )

        balanced_accuracy = balanced_accuracy_score(
            labels,
            predictions,
        )

        matrix = confusion_matrix(
            labels,
            predictions,
            labels=[0, 1],
        )

        tn, fp, fn, tp = matrix.ravel()

        roc_auc = None
        pr_auc = None
        average_precision = None

        if len(np.unique(labels)) == 2:

            roc_auc = float(
                roc_auc_score(
                    labels,
                    probabilities,
                )
            )

            precision_curve, recall_curve, _ = (
                precision_recall_curve(
                    labels,
                    probabilities,
                )
            )

            pr_auc = float(
                auc(
                    recall_curve,
                    precision_curve,
                )
            )

            average_precision = float(
                average_precision_score(
                    labels,
                    probabilities,
                )
            )

        return ClassificationMetrics(
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            balanced_accuracy=float(balanced_accuracy),
            roc_auc=roc_auc,
            pr_auc=pr_auc,
            average_precision=average_precision,
            confusion_matrix=(
                (
                    int(tn),
                    int(fp),
                ),
                (
                    int(fn),
                    int(tp),
                ),
            ),
            true_positives=int(tp),
            true_negatives=int(tn),
            false_positives=int(fp),
            false_negatives=int(fn),
            threshold=self.config.classification_threshold,
        )

    # ---------------------------------------------------------
    # Class imbalance
    # ---------------------------------------------------------

    @staticmethod
    def _class_distribution(
        labels: np.ndarray,
    ) -> ClassDistribution:

        total = len(labels)

        relevant = int(np.sum(labels == 1))

        not_relevant = int(np.sum(labels == 0))

        relevant_ratio = relevant / total

        not_relevant_ratio = not_relevant / total

        imbalance_ratio = (
            max(relevant, not_relevant)
            / min(relevant, not_relevant)
            if min(relevant, not_relevant) > 0
            else None
        )

        return ClassDistribution(
            total_samples=total,
            relevant_samples=relevant,
            not_relevant_samples=not_relevant,
            relevant_ratio=float(relevant_ratio),
            not_relevant_ratio=float(not_relevant_ratio),
            imbalance_ratio=(
                float(imbalance_ratio)
                if imbalance_ratio is not None
                else None
            ),
        )

    # ---------------------------------------------------------
    # Ranking metrics
    # ---------------------------------------------------------

    def _ranking_metrics(
        self,
        labels: np.ndarray,
        probabilities: np.ndarray,
        user_ids: Sequence,
        resource_ids: Sequence,
    ) -> RankingMetrics:

        grouped = defaultdict(list)

        for label, score, user_id, resource_id in zip(
            labels,
            probabilities,
            user_ids,
            resource_ids,
        ):
            grouped[user_id].append(
                (
                    int(label),
                    float(score),
                    str(resource_id),
                )
            )

        precision_values = {
            k: []
            for k in self.config.ranking_k_values
        }

        recall_values = {
            k: []
            for k in self.config.ranking_k_values
        }

        ndcg_values = {
            k: []
            for k in self.config.ranking_k_values
        }

        users_without_relevant_items = 0

        for candidates in grouped.values():

            # Deterministic tie-breaking by resource ID.
            ranked = sorted(
                candidates,
                key=lambda item: (
                    -item[1],
                    item[2],
                ),
            )

            relevance = np.asarray(
                [item[0] for item in ranked],
                dtype=np.int64,
            )

            relevant_count = int(
                np.sum(relevance == 1)
            )

            if relevant_count == 0:
                users_without_relevant_items += 1

            for k in self.config.ranking_k_values:

                top_k = relevance[:k]

                relevant_in_top_k = int(
                    np.sum(top_k == 1)
                )

                precision_values[k].append(
                    relevant_in_top_k / k
                )

                # Recall is undefined for a user with no
                # relevant ground-truth candidates.
                if relevant_count > 0:
                    recall_values[k].append(
                        relevant_in_top_k / relevant_count
                    )

                ndcg = ndcg_score(
                    relevance.reshape(1, -1),
                    np.asarray(
                        [
                            [
                                item[1]
                                for item in ranked
                            ]
                        ],
                        dtype=np.float64,
                    ),
                    k=min(k, len(ranked)),
                )

                ndcg_values[k].append(
                    float(ndcg)
                )

        return RankingMetrics(
            precision_at_k={
                k: float(np.mean(values))
                for k, values in precision_values.items()
            },
            recall_at_k={
                k: (
                    float(np.mean(values))
                    if values
                    else 0.0
                )
                for k, values in recall_values.items()
            },
            ndcg_at_k={
                k: float(np.mean(values))
                for k, values in ndcg_values.items()
            },
            evaluated_users=len(grouped),
            users_without_relevant_items=(
                users_without_relevant_items
            ),
        )

    # ---------------------------------------------------------
    # Complete model evaluation
    # ---------------------------------------------------------

    def _evaluate_model(
        self,
        model_name: str,
        model,
        features,
        data: _ValidatedEvaluationData,
    ) -> ModelEvaluation:

        probabilities = self._get_positive_probabilities(
            model=model,
            features=features,
            sample_count=data.sample_count,
        )

        classification = self._classification_metrics(
            labels=data.labels,
            probabilities=probabilities,
        )

        ranking = self._ranking_metrics(
            labels=data.labels,
            probabilities=probabilities,
            user_ids=data.user_ids,
            resource_ids=data.resource_ids,
        )

        distribution = self._class_distribution(
            data.labels,
        )

        return ModelEvaluation(
            model_name=model_name,
            classification=classification,
            ranking=ranking,
            class_distribution=distribution,
        )

    # ---------------------------------------------------------
    # Baseline comparison
    # ---------------------------------------------------------

    @staticmethod
    def _compare(
        model: ModelEvaluation,
        baseline: ModelEvaluation,
    ) -> tuple[MetricComparison, ...]:

        metrics = (
            ("accuracy", "accuracy"),
            ("precision", "precision"),
            ("recall", "recall"),
            ("f1_score", "f1_score"),
            ("balanced_accuracy", "balanced_accuracy"),
            ("roc_auc", "roc_auc"),
            ("pr_auc", "pr_auc"),
            ("average_precision", "average_precision"),
        )

        comparisons = []

        for metric_name, attribute in metrics:

            model_value = getattr(
                model.classification,
                attribute,
            )

            baseline_value = getattr(
                baseline.classification,
                attribute,
            )

            improvement = (
                model_value - baseline_value
                if model_value is not None
                and baseline_value is not None
                else None
            )

            comparisons.append(
                MetricComparison(
                    metric_name=metric_name,
                    model_value=model_value,
                    baseline_value=baseline_value,
                    improvement=improvement,
                )
            )

        for k in model.ranking.ndcg_at_k:

            model_value = model.ranking.ndcg_at_k[k]

            baseline_value = baseline.ranking.ndcg_at_k[k]

            comparisons.append(
                MetricComparison(
                    metric_name=f"ndcg_at_{k}",
                    model_value=model_value,
                    baseline_value=baseline_value,
                    improvement=model_value - baseline_value,
                )
            )

        return tuple(comparisons)

    # ---------------------------------------------------------
    # Public evaluation API
    # ---------------------------------------------------------

    def evaluate(
        self,
        training_result: TrainingResult,
    ) -> EvaluationReport:
        """
        Evaluate the trained model against its dummy baseline.

        Uses only the held-out validation dataset.
        """

        data = self._validate_evaluation_data(
            training_result,
        )

        dataset = training_result.evaluation_dataset

        trained_model = self._evaluate_model(
            model_name="logistic_regression",
            model=training_result.model,
            features=dataset.X,
            data=data,
        )

        dummy_baseline = self._evaluate_model(
            model_name="dummy_classifier",
            model=training_result.dummy_baseline,
            features=dataset.X,
            data=data,
        )

        comparisons = self._compare(
            model=trained_model,
            baseline=dummy_baseline,
        )

        model_ap = (
            trained_model.classification.average_precision
        )

        baseline_ap = (
            dummy_baseline.classification.average_precision
        )

        model_ndcg = trained_model.ranking.ndcg_at_k

        baseline_ndcg = dummy_baseline.ranking.ndcg_at_k

        # The learned model must not be declared superior
        # based only on accuracy.
        model_outperforms_dummy = (
            model_ap is not None
            and baseline_ap is not None
            and model_ap > baseline_ap
            and all(
                model_ndcg[k] >= baseline_ndcg[k]
                for k in model_ndcg
            )
        )

        notes = [
            "Evaluation used held-out validation data.",
            "The feature transformer was not refitted.",
            "Ranking metrics were calculated separately per user.",
            "Validation labels were used as ground truth.",
            "The dummy baseline was evaluated on the same candidates.",
        ]

        if data.sample_count < 100:
            notes.append(
                "Validation sample count is small; "
                "metric estimates may be unstable."
            )

        if (
            trained_model.class_distribution.imbalance_ratio
            is not None
            and trained_model.class_distribution.imbalance_ratio >= 3
        ):
            notes.append(
                "Class imbalance detected. "
                "Interpret accuracy alongside precision, recall, "
                "F1, PR-AUC and balanced accuracy."
            )

        return EvaluationReport(
            run_id=training_result.run_id,
            evaluated_at=datetime.now(
                timezone.utc
            ).isoformat(),
            trained_model=trained_model,
            dummy_baseline=dummy_baseline,
            comparisons=comparisons,
            model_outperforms_dummy=bool(
                model_outperforms_dummy
            ),
            notes=tuple(notes),
        )