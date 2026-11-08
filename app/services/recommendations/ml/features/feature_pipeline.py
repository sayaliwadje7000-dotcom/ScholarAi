"""End-to-end recommendation feature pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from app.models.study_resource import StudyResource
from app.models.user_preferences import UserPreferences
from app.models.user_resource_interaction import (
    UserResourceInteraction,
)

from app.services.recommendations.ml.features.feature_extractor import (
    RecommendationFeatureExtractor,
)

from app.services.recommendations.ml.features.feature_schema import (
    RecommendationFeatureRow,
)

from app.services.recommendations.ml.features.feature_transformer import (
    FeatureTransformationResult,
    RecommendationFeatureTransformer,
)


@dataclass(frozen=True, slots=True)
class FeaturePipelineResult:

    rows: tuple[RecommendationFeatureRow, ...]

    transformation: FeatureTransformationResult


class RecommendationFeaturePipeline:
    """
    Coordinates feature extraction and transformation.

    This pipeline does not access the database itself.
    """

    def __init__(
        self,
        extractor: RecommendationFeatureExtractor | None = None,
        transformer: RecommendationFeatureTransformer | None = None,
    ) -> None:

        self.extractor = (
            extractor or RecommendationFeatureExtractor()
        )

        self.transformer = (
            transformer or RecommendationFeatureTransformer()
        )

    def extract_rows(
        self,
        candidates: Iterable[dict[str, Any]],
    ) -> tuple[RecommendationFeatureRow, ...]:

        rows = []

        for candidate in candidates:

            row = self.extractor.extract(
                user_id=candidate["user_id"],
                resource=candidate["resource"],
                preferences=candidate.get("preferences"),
                interactions=candidate.get(
                    "interactions",
                    (),
                ),
                prediction_at=candidate["prediction_at"],
                resource_embedding=candidate.get(
                    "resource_embedding"
                ),
            )

            rows.append(row)

        return tuple(rows)

    @staticmethod
    def _model_records(
        rows: tuple[RecommendationFeatureRow, ...],
    ) -> list[dict]:

        return [
            row.to_model_features()
            for row in rows
        ]

    def fit_transform(
        self,
        candidates: Iterable[dict[str, Any]],
    ) -> FeaturePipelineResult:

        rows = self.extract_rows(candidates)

        if not rows:
            raise ValueError(
                "No feature rows were generated"
            )

        transformation = self.transformer.fit_transform(
            self._model_records(rows)
        )

        return FeaturePipelineResult(
            rows=rows,
            transformation=transformation,
        )

    def transform(
        self,
        candidates: Iterable[dict[str, Any]],
    ) -> FeaturePipelineResult:

        rows = self.extract_rows(candidates)

        if not rows:
            raise ValueError(
                "No feature rows were generated"
            )

        transformation = self.transformer.transform(
            self._model_records(rows)
        )

        return FeaturePipelineResult(
            rows=rows,
            transformation=transformation,
        )