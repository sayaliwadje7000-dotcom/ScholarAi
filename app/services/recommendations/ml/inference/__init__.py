"""ML recommendation inference package."""

from app.services.recommendations.ml.inference.inference_config import (
    RecommendationInferenceConfig,
)

from app.services.recommendations.ml.inference.inference_exceptions import (
    InferenceError,
    InferenceInputError,
    ModelNotAvailableError,
    ModelCompatibilityError,
    PredictionError,
)

from app.services.recommendations.ml.inference.inference_result import (
    RecommendationPrediction,
    RecommendationPredictionBatch,
)

from app.services.recommendations.ml.inference.recommendation_service import (
    RecommendationMLService,
)

__all__ = [
    "RecommendationInferenceConfig",
    "InferenceError",
    "InferenceInputError",
    "ModelNotAvailableError",
    "ModelCompatibilityError",
    "PredictionError",
    "RecommendationPrediction",
    "RecommendationPredictionBatch",
    "RecommendationMLService",
]