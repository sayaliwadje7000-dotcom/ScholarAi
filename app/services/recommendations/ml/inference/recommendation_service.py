"""ML recommendation inference service."""

from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

import numpy as np

from app.services.recommendations.ml.features.feature_extractor import (
    RecommendationFeatureExtractor,
)

from app.services.recommendations.ml.inference.inference_config import (
    RecommendationInferenceConfig,
)

from app.services.recommendations.ml.inference.inference_exceptions import (
    InferenceInputError,
    ModelCompatibilityError,
    ModelNotAvailableError,
    PredictionError,
)

from app.services.recommendations.ml.inference.inference_result import (
    RecommendationPrediction,
    RecommendationPredictionBatch,
)


class RecommendationMLService:
    """
    Performs inference using a previously trained recommendation model.

    Responsibilities:
    - Validate inference inputs.
    - Extract candidate resource features.
    - Transform features using the fitted transformer.
    - Calculate relevance probabilities.
    - Return structured predictions.

    This service does not:
    - Train models.
    - Fit feature transformers.
    - Query the database directly.
    - Modify recommendation records.
    """

    def __init__(
        self,
        model: Any | None,
        feature_transformer: Any | None,
        feature_extractor: RecommendationFeatureExtractor,
        model_run_id: str | None,
        config: RecommendationInferenceConfig | None = None,
    ) -> None:
        self.model = model
        self.feature_transformer = feature_transformer
        self.feature_extractor = feature_extractor
        self.model_run_id = model_run_id
        self.config = config or RecommendationInferenceConfig()

        self._validate_model_bundle()

    def _validate_model_bundle(self) -> None:
        """Validate the availability and compatibility of model components."""

        if self.model is None:
            raise ModelNotAvailableError(
                "No trained recommendation model is available."
            )

        if self.feature_transformer is None:
            raise ModelNotAvailableError(
                "No fitted recommendation feature transformer is available."
            )

        if self.feature_extractor is None:
            raise ModelNotAvailableError(
                "Recommendation feature extractor is unavailable."
            )

        if not isinstance(self.model_run_id, str) or not self.model_run_id.strip():
            raise ModelCompatibilityError(
                "A valid model run ID is required."
            )

        if not callable(
            getattr(self.feature_transformer, "transform", None)
        ):
            raise ModelCompatibilityError(
                "Feature transformer must provide transform()."
            )

        if not callable(
            getattr(self.model, "predict_relevance_probability", None)
        ):
            raise ModelCompatibilityError(
                "Model must provide predict_relevance_probability()."
            )

        if not callable(
            getattr(self.feature_extractor, "extract", None)
        ):
            raise ModelCompatibilityError(
                "Feature extractor must provide extract()."
            )

    def is_available(self) -> bool:
        """Return whether the inference bundle is available."""

        try:
            self._validate_model_bundle()
        except (
            ModelNotAvailableError,
            ModelCompatibilityError,
        ):
            return False

        return True

    @staticmethod
    def _validate_identifiers(
        user_id: UUID,
        resource_ids: Sequence[UUID],
    ) -> None:
        if not isinstance(user_id, UUID):
            raise InferenceInputError(
                "User ID must be a UUID."
            )

        if isinstance(resource_ids, (str, bytes)):
            raise InferenceInputError(
                "Resource IDs must be a sequence of UUID values."
            )

        for resource_id in resource_ids:
            if not isinstance(resource_id, UUID):
                raise InferenceInputError(
                    "Every resource ID must be a UUID."
                )

        if len(resource_ids) != len(set(resource_ids)):
            raise InferenceInputError(
                "Duplicate resource IDs are not permitted."
            )

    def _validate_candidate_count(
        self,
        resource_ids: Sequence[UUID],
    ) -> None:
        candidate_count = len(resource_ids)

        if candidate_count == 0:
            if self.config.allow_empty_predictions:
                return

            raise InferenceInputError(
                "At least one candidate resource is required."
            )

        if candidate_count < self.config.minimum_candidates:
            raise InferenceInputError(
                "Candidate count is below the configured minimum."
            )

        if candidate_count > self.config.maximum_candidates:
            raise InferenceInputError(
                "Candidate count exceeds the configured maximum."
            )

    @staticmethod
    def _validate_probabilities(
        probabilities: Any,
        expected_count: int,
    ) -> np.ndarray:
        """Validate model output before creating prediction records."""

        try:
            values = np.asarray(
                probabilities,
                dtype=np.float64,
            )
        except (TypeError, ValueError) as exc:
            raise PredictionError(
                "Model returned non-numeric prediction values."
            ) from exc

        if values.ndim != 1:
            raise PredictionError(
                "Model must return one probability per candidate."
            )

        if len(values) != expected_count:
            raise PredictionError(
                "Prediction count does not match candidate count."
            )

        if not np.isfinite(values).all():
            raise PredictionError(
                "Model returned non-finite prediction values."
            )

        if ((values < 0.0) | (values > 1.0)).any():
            raise PredictionError(
                "Model returned probabilities outside [0, 1]."
            )

        return values

    def predict(
        self,
        user_id: UUID,
        resource_ids: Sequence[UUID],
        prediction_at: Any | None = None,
    ) -> RecommendationPredictionBatch:
        """
        Generate relevance predictions for candidate resources.

        Feature extraction is delegated to the existing feature extractor.
        The fitted transformer is only used for transform(), never fit().
        """

        self._validate_model_bundle()

        self._validate_identifiers(
            user_id,
            resource_ids,
        )

        self._validate_candidate_count(resource_ids)

        if not resource_ids:
            return RecommendationPredictionBatch.create(
                user_id=user_id,
                predictions=(),
                model_run_id=self.model_run_id,
                prediction_threshold=self.config.relevance_threshold,
            )

        try:
            feature_rows = self.feature_extractor.extract(
                user_id=user_id,
                resource_ids=list(resource_ids),
                prediction_at=prediction_at,
            )

        except Exception as exc:
            raise PredictionError(
                "Unable to extract recommendation inference features."
            ) from exc

        if len(feature_rows) != len(resource_ids):
            raise PredictionError(
                "Feature extractor returned an unexpected number of rows."
            )

        returned_resource_ids = [
            getattr(row, "resource_id", None)
            for row in feature_rows
        ]

        if returned_resource_ids != list(resource_ids):
            raise PredictionError(
                "Feature rows do not preserve the requested resource order."
            )

        try:
            model_records = [
                row.to_model_features()
                for row in feature_rows
            ]

        except Exception as exc:
            raise PredictionError(
                "Unable to convert feature rows into model records."
            ) from exc

        try:
            transformed = self.feature_transformer.transform(
                model_records
            )

        except Exception as exc:
            raise ModelCompatibilityError(
                "The fitted feature transformer rejected inference features."
            ) from exc

        matrix = getattr(
            transformed,
            "matrix",
            transformed,
        )

        try:
            probabilities = (
                self.model.predict_relevance_probability(matrix)
            )

        except Exception as exc:
            raise PredictionError(
                "Recommendation model prediction failed."
            ) from exc

        probabilities = self._validate_probabilities(
            probabilities,
            expected_count=len(resource_ids),
        )

        predictions = tuple(
            RecommendationPrediction(
                resource_id=resource_id,
                relevance_probability=float(probability),
                is_relevant=(
                    float(probability)
                    >= self.config.relevance_threshold
                ),
                model_run_id=self.model_run_id,
            )
            for resource_id, probability in zip(
                resource_ids,
                probabilities,
            )
        )

        return RecommendationPredictionBatch.create(
            user_id=user_id,
            predictions=predictions,
            model_run_id=self.model_run_id,
            prediction_threshold=self.config.relevance_threshold,
        )