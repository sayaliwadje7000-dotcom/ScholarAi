"""Structured results returned by recommendation inference."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RecommendationPrediction:
    """Prediction for one candidate resource."""

    resource_id: UUID

    relevance_probability: float

    is_relevant: bool

    model_run_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, UUID):
            raise TypeError(
                "Resource ID must be a UUID."
            )

        if not 0.0 <= self.relevance_probability <= 1.0:
            raise ValueError(
                "Relevance probability must be between 0 and 1."
            )

        if not self.model_run_id:
            raise ValueError(
                "Model run ID cannot be empty."
            )


@dataclass(frozen=True, slots=True)
class RecommendationPredictionBatch:
    """Collection of predictions from one inference operation."""

    user_id: UUID

    predictions: tuple[RecommendationPrediction, ...]

    model_run_id: str

    prediction_threshold: float

    generated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError(
                "User ID must be a UUID."
            )

        if not 0.0 <= self.prediction_threshold <= 1.0:
            raise ValueError(
                "Prediction threshold must be between 0 and 1."
            )

        if not self.model_run_id:
            raise ValueError(
                "Model run ID cannot be empty."
            )

        if self.generated_at.tzinfo is None:
            raise ValueError(
                "Generated timestamp must be timezone-aware."
            )

        resource_ids = [
            prediction.resource_id
            for prediction in self.predictions
        ]

        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError(
                "Prediction batch contains duplicate resources."
            )

        if any(
            prediction.model_run_id != self.model_run_id
            for prediction in self.predictions
        ):
            raise ValueError(
                "Prediction model run IDs do not match batch run ID."
            )

    @classmethod
    def create(
        cls,
        user_id: UUID,
        predictions: tuple[RecommendationPrediction, ...],
        model_run_id: str,
        prediction_threshold: float,
    ) -> RecommendationPredictionBatch:
        return cls(
            user_id=user_id,
            predictions=predictions,
            model_run_id=model_run_id,
            prediction_threshold=prediction_threshold,
            generated_at=datetime.now(timezone.utc),
        )