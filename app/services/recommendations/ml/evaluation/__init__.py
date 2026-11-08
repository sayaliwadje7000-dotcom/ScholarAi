"""Model evaluation and validation for ScholarAI."""

from app.services.recommendations.ml.evaluation.evaluation_config import (
    EvaluationConfig,
    EvaluationConfigurationError,
)

from app.services.recommendations.ml.evaluation.evaluation_metrics import (
    ClassificationMetrics,
    ClassDistribution,
    EvaluationReport,
    MetricComparison,
    ModelEvaluation,
    RankingMetrics,
)

from app.services.recommendations.ml.evaluation.evaluation_service import (
    EvaluationInputError,
    EvaluationPredictionError,
    ModelEvaluationError,
    RecommendationModelEvaluator,
)

__all__ = [
    "EvaluationConfig",
    "EvaluationConfigurationError",
    "ClassificationMetrics",
    "ClassDistribution",
    "EvaluationReport",
    "MetricComparison",
    "ModelEvaluation",
    "RankingMetrics",
    "EvaluationInputError",
    "EvaluationPredictionError",
    "ModelEvaluationError",
    "RecommendationModelEvaluator",
]