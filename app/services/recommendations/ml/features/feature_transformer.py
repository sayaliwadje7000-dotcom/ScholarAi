"""Machine-learning feature transformation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CATEGORICAL_FEATURES = [
    "preferred_language",
    "education_level",
    "resource_type",
    "subject",
    "language",
    "difficulty_level",
    "provider",
]


NUMERICAL_FEATURES = [
    "quality_score",
    "estimated_duration_minutes",
    "resource_age_days",
    "historical_view_count",
    "historical_click_count",
    "historical_save_count",
    "historical_completion_count",
    "historical_rating_count",
    "historical_average_rating",
]


TEXT_FEATURES = [
    "preferred_subjects",
    "learning_goals",
    "categories",
    "title",
    "description",
    "topics",
    "keywords",
    "learning_objectives",
    "prerequisites",
]


@dataclass(frozen=True, slots=True)
class FeatureTransformationResult:

    matrix: object

    feature_names: tuple[str, ...]

    row_count: int

    feature_count: int


class RecommendationFeatureTransformer:
    """
    Transforms structured recommendation features into
    a reproducible numerical feature matrix.
    """

    def __init__(
        self,
        max_text_features: int = 5000,
        embedding_dimensions: int | None = None,
    ) -> None:

        if max_text_features < 1:
            raise ValueError(
                "max_text_features must be positive"
            )

        if (
            embedding_dimensions is not None
            and embedding_dimensions < 1
        ):
            raise ValueError(
                "embedding_dimensions must be positive"
            )

        self.max_text_features = max_text_features

        self.embedding_dimensions = embedding_dimensions

        categorical_pipeline = Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="constant",
                        fill_value="__missing__",
                    ),
                ),
                (
                    "encoder",
                    OneHotEncoder(
                        handle_unknown="ignore",
                    ),
                ),
            ]
        )

        numerical_pipeline = Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median",
                        keep_empty_features=True,
                    ),
                ),
                (
                    "scaler",
                    StandardScaler(),
                ),
            ]
        )

        self.column_transformer = ColumnTransformer(
            transformers=[
                (
                    "categorical",
                    categorical_pipeline,
                    CATEGORICAL_FEATURES,
                ),
                (
                    "numerical",
                    numerical_pipeline,
                    NUMERICAL_FEATURES,
                ),
                (
                    "text",
                    TfidfVectorizer(
                        max_features=max_text_features,
                        ngram_range=(1, 2),
                        sublinear_tf=True,
                        token_pattern=r"(?u)\b\w+\b",
                    ),
                    "combined_text",
                ),
            ],
            remainder="drop",
            sparse_threshold=1.0,
        )

        self._is_fitted = False

    @staticmethod
    def _combine_text(row: dict) -> str:

        parts = []

        for field in TEXT_FEATURES:

            value = row.get(field)

            if value is None:
                continue

            if isinstance(value, (list, tuple)):

                parts.extend(
                    str(item)
                    for item in value
                    if item
                )

            elif isinstance(value, str) and value.strip():

                parts.append(value)

        return " ".join(parts)

    def _prepare_dataframe(
        self,
        records: list[dict],
    ) -> pd.DataFrame:

        if not records:
            raise ValueError(
                "Cannot transform an empty feature dataset"
            )

        frame = pd.DataFrame(records)

        required = (
            CATEGORICAL_FEATURES
            + NUMERICAL_FEATURES
            + TEXT_FEATURES
        )

        for column in required:

            if column not in frame.columns:
                frame[column] = None

        for column in CATEGORICAL_FEATURES:

            frame[column] = frame[column].map(
                lambda value: (
                    str(value)
                    if value is not None
                    else None
                )
            )

        for column in NUMERICAL_FEATURES:

            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

        frame["combined_text"] = frame.apply(
            lambda row: self._combine_text(
                row.to_dict()
            ),
            axis=1,
        )

        return frame

    def fit_transform(
        self,
        records: list[dict],
    ) -> FeatureTransformationResult:

        frame = self._prepare_dataframe(records)

        matrix = self.column_transformer.fit_transform(
            frame
        )

        self._is_fitted = True

        feature_names = tuple(
            self.column_transformer.get_feature_names_out()
        )

        return FeatureTransformationResult(
            matrix=matrix,
            feature_names=feature_names,
            row_count=matrix.shape[0],
            feature_count=matrix.shape[1],
        )

    def transform(
        self,
        records: list[dict],
    ) -> FeatureTransformationResult:

        if not self._is_fitted:
            raise RuntimeError(
                "Feature transformer must be fitted first"
            )

        frame = self._prepare_dataframe(records)

        matrix = self.column_transformer.transform(
            frame
        )

        feature_names = tuple(
            self.column_transformer.get_feature_names_out()
        )

        return FeatureTransformationResult(
            matrix=matrix,
            feature_names=feature_names,
            row_count=matrix.shape[0],
            feature_count=matrix.shape[1],
        )