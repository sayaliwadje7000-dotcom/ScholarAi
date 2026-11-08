"""ScholarAI recommendation machine-learning models."""

from app.services.recommendations.ml.models.model_config import (
    BaselineModelConfig,
)

from app.services.recommendations.ml.models.baseline_model import (
    BaselineModelError,
    BaselineModelNotFittedError,
    InvalidTrainingDataError,
    BaselineTrainingSummary,
    FeatureCoefficient,
    RecommendationBaselineModel,
    RecommendationDummyBaseline,
)


__all__ = [
    "BaselineModelConfig",
    "BaselineModelError",
    "BaselineModelNotFittedError",
    "InvalidTrainingDataError",
    "BaselineTrainingSummary",
    "FeatureCoefficient",
    "RecommendationBaselineModel",
    "RecommendationDummyBaseline",
]