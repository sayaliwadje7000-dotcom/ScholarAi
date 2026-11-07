from __future__ import annotations

import math

from dataclasses import dataclass
from uuid import UUID

from app.services.recommendations.content_based.feature_extractor import (
    ExtractedContentFeatures,
)

from app.services.recommendations.content_based.scoring_models import (
    ContentBasedScoreResult,
)


class ContentCandidateValidationError(ValueError):
    """Raised when a content-based candidate is invalid."""


@dataclass(frozen=True, slots=True)
class ContentBasedCandidate:

    features: ExtractedContentFeatures

    scoring_result: ContentBasedScoreResult

    is_active: bool = True

    quality_score: float | None = None

    def __post_init__(self):

        if not isinstance(
            self.features,
            ExtractedContentFeatures,
        ):
            raise ContentCandidateValidationError(
                "features must be ExtractedContentFeatures."
            )

        if not isinstance(
            self.scoring_result,
            ContentBasedScoreResult,
        ):
            raise ContentCandidateValidationError(
                "scoring_result must be ContentBasedScoreResult."
            )

        if not isinstance(self.is_active, bool):
            raise ContentCandidateValidationError(
                "is_active must be a boolean."
            )

        if self.features.resource_id != (
            self.scoring_result.candidate_resource_id
        ):
            raise ContentCandidateValidationError(
                "Candidate resource ID does not match scoring result."
            )

        if not isinstance(
            self.scoring_result.reference_resource_id,
            UUID,
        ):
            raise ContentCandidateValidationError(
                "Reference resource ID must be a UUID."
            )

        if not isinstance(
            self.scoring_result.candidate_resource_id,
            UUID,
        ):
            raise ContentCandidateValidationError(
                "Candidate resource ID must be a UUID."
            )

        self._validate_score(
            self.scoring_result.score,
            "score",
        )

        self._validate_score(
            self.scoring_result.confidence,
            "confidence",
        )

        if self.quality_score is not None:

            self._validate_score(
                self.quality_score,
                "quality_score",
                maximum=5.0,
            )

    @staticmethod
    def _validate_score(
        value: float,
        name: str,
        maximum: float = 1.0,
    ):

        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise ContentCandidateValidationError(
                f"{name} must be numeric."
            )

        if not math.isfinite(value):
            raise ContentCandidateValidationError(
                f"{name} must be finite."
            )

        if not 0.0 <= value <= maximum:
            raise ContentCandidateValidationError(
                f"{name} must be between 0 and {maximum}."
            )

    @property
    def resource_id(self) -> UUID:

        return self.features.resource_id

    @property
    def score(self) -> float:

        return self.scoring_result.score

    @property
    def confidence(self) -> float:

        return self.scoring_result.confidence