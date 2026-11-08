"""Evaluation result structures for recommendation models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class ClassificationMetrics:
    """Binary classification performance metrics."""

    accuracy: float
    precision: float
    recall: float
    f1_score: float
    balanced_accuracy: float

    roc_auc: float | None
    pr_auc: float | None
    average_precision: float | None

    confusion_matrix: tuple[
        tuple[int, int],
        tuple[int, int],
    ]

    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int

    threshold: float


@dataclass(frozen=True, slots=True)
class RankingMetrics:
    """Per-user recommendation ranking metrics."""

    precision_at_k: dict[int, float]

    recall_at_k: dict[int, float]

    ndcg_at_k: dict[int, float]

    evaluated_users: int

    users_without_relevant_items: int


@dataclass(frozen=True, slots=True)
class ClassDistribution:
    """Ground-truth class distribution."""

    total_samples: int

    relevant_samples: int

    not_relevant_samples: int

    relevant_ratio: float

    not_relevant_ratio: float

    imbalance_ratio: float | None


@dataclass(frozen=True, slots=True)
class ModelEvaluation:
    """Complete evaluation of one recommendation model."""

    model_name: str

    classification: ClassificationMetrics

    ranking: RankingMetrics

    class_distribution: ClassDistribution

    def to_dict(self) -> dict:
        """Convert evaluation results into JSON-compatible data."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class MetricComparison:
    """Comparison between the trained model and dummy baseline."""

    metric_name: str

    model_value: float | None

    baseline_value: float | None

    improvement: float | None


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Complete validation report for a training run."""

    run_id: str

    evaluated_at: str

    trained_model: ModelEvaluation

    dummy_baseline: ModelEvaluation

    comparisons: tuple[MetricComparison, ...]

    model_outperforms_dummy: bool

    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        """Return a JSON-compatible evaluation report."""

        return asdict(self)