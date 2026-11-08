"""Configuration for ML recommendation inference."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecommendationInferenceConfig:
    """Controls recommendation-model inference."""

    relevance_threshold: float = 0.5

    maximum_candidates: int = 500

    minimum_candidates: int = 1

    allow_empty_predictions: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.relevance_threshold <= 1.0:
            raise ValueError(
                "Relevance threshold must be between 0 and 1."
            )

        if self.minimum_candidates < 0:
            raise ValueError(
                "Minimum candidates cannot be negative."
            )

        if self.maximum_candidates < 1:
            raise ValueError(
                "Maximum candidates must be at least 1."
            )

        if self.minimum_candidates > self.maximum_candidates:
            raise ValueError(
                "Minimum candidates cannot exceed maximum candidates."
            )