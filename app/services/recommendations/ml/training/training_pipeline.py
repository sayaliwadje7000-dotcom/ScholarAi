"""Reproducible training pipeline for ScholarAI recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from app.services.recommendations.ml.dataset_schema import (
    DatasetLabel,
    RecommendationTrainingExample,
)
from app.services.recommendations.ml.features.feature_schema import (
    RecommendationFeatureRow,
)
from app.services.recommendations.ml.features.feature_transformer import (
    RecommendationFeatureTransformer,
)
from app.services.recommendations.ml.models.baseline_model import (
    BaselineTrainingSummary,
    RecommendationBaselineModel,
    RecommendationDummyBaseline,
)
from app.services.recommendations.ml.training.training_config import (
    TrainingConfig,
)


class TrainingPipelineError(Exception):
    """Base exception for recommendation training failures."""


class DatasetAlignmentError(TrainingPipelineError):
    """Raised when labels and feature rows cannot be aligned."""


class DatasetSplitError(TrainingPipelineError):
    """Raised when a valid user-separated split cannot be produced."""


@dataclass(frozen=True, slots=True)
class DatasetStatistics:
    """Summary statistics for a labelled dataset partition."""

    total_samples: int
    relevant_samples: int
    not_relevant_samples: int
    unique_users: int
    unique_resources: int

    @property
    def relevant_ratio(self) -> float:
        if self.total_samples == 0:
            return 0.0

        return self.relevant_samples / self.total_samples


@dataclass(frozen=True, slots=True)
class EvaluationDataset:
    """
    Held-out validation data for Phase 14.6.

    Contains internal identifiers for grouping and evaluation.
    These identifiers are not passed to the model.
    """

    X: object
    y: np.ndarray
    user_ids: tuple[UUID, ...]
    resource_ids: tuple[UUID, ...]
    statistics: DatasetStatistics


@dataclass(frozen=True, slots=True)
class TrainingResult:
    """Result of a completed training run."""

    run_id: str
    trained_at: datetime

    model: RecommendationBaselineModel
    dummy_baseline: RecommendationDummyBaseline
    feature_transformer: RecommendationFeatureTransformer

    training_summary: BaselineTrainingSummary

    training_statistics: DatasetStatistics
    validation_statistics: DatasetStatistics

    feature_names: tuple[str, ...]

    # User identifiers are retained for split auditing.
    training_user_ids: tuple[UUID, ...]
    validation_user_ids: tuple[UUID, ...]

    training_class_distribution: dict[int, int]
    validation_class_distribution: dict[int, int]

    evaluation_dataset: EvaluationDataset
    config: TrainingConfig


class RecommendationTrainingPipeline:
    """
    Coordinates dataset validation, splitting, transformation,
    and baseline model training.

    The pipeline does not access PostgreSQL.

    Inputs:
        RecommendationFeatureRow objects.
        RecommendationTrainingExample objects.
    """

    def __init__(
        self,
        config: TrainingConfig | None = None,
        feature_transformer: RecommendationFeatureTransformer | None = None,
        model: RecommendationBaselineModel | None = None,
        dummy_baseline: RecommendationDummyBaseline | None = None,
    ) -> None:

        self.config = config or TrainingConfig()

        self.feature_transformer = (
            feature_transformer
            or RecommendationFeatureTransformer()
        )

        self.model = (
            model
            or RecommendationBaselineModel()
        )

        self.dummy_baseline = (
            dummy_baseline
            or RecommendationDummyBaseline()
        )

    @staticmethod
    def _statistics(
        rows: Sequence[RecommendationFeatureRow],
        labels: np.ndarray,
    ) -> DatasetStatistics:

        return DatasetStatistics(
            total_samples=len(rows),
            relevant_samples=int(
                np.sum(labels == int(DatasetLabel.RELEVANT))
            ),
            not_relevant_samples=int(
                np.sum(labels == int(DatasetLabel.NOT_RELEVANT))
            ),
            unique_users=len({
                row.user_id for row in rows
            }),
            unique_resources=len({
                row.resource_id for row in rows
            }),
        )

    @staticmethod
    def _class_distribution(
        labels: np.ndarray,
    ) -> dict[int, int]:

        unique_labels, counts = np.unique(
            labels,
            return_counts=True,
        )

        return {
            int(label): int(count)
            for label, count in zip(unique_labels, counts)
        }

    @staticmethod
    def _validate_inputs(
        feature_rows: Sequence[RecommendationFeatureRow],
        examples: Sequence[RecommendationTrainingExample],
    ) -> tuple[list[RecommendationFeatureRow], np.ndarray]:

        if not feature_rows:
            raise DatasetAlignmentError(
                "Feature dataset cannot be empty"
            )

        if not examples:
            raise DatasetAlignmentError(
                "Label dataset cannot be empty"
            )

        feature_map = {}

        for row in feature_rows:
            if row.grouping_key in feature_map:
                raise DatasetAlignmentError(
                    "Duplicate user-resource feature rows detected"
                )

            feature_map[row.grouping_key] = row

        label_map = {}

        for example in examples:
            if example.sample_key in label_map:
                raise DatasetAlignmentError(
                    "Duplicate user-resource labels detected"
                )

            label_map[example.sample_key] = example

        feature_keys = set(feature_map)
        label_keys = set(label_map)

        if feature_keys != label_keys:
            missing_features = label_keys - feature_keys
            missing_labels = feature_keys - label_keys

            raise DatasetAlignmentError(
                "Feature-label alignment failed. "
                f"Missing feature rows: {len(missing_features)}. "
                f"Missing labels: {len(missing_labels)}."
            )

        ordered_rows = []
        ordered_examples = []

        # Stable ordering makes dataset preparation reproducible.
        for key in sorted(
            feature_keys,
            key=lambda item: (
                str(item[0]),
                str(item[1]),
            ),
        ):
            ordered_rows.append(feature_map[key])
            ordered_examples.append(label_map[key])

        labels = np.asarray(
            [
                int(example.label)
                for example in ordered_examples
            ],
            dtype=np.int64,
        )

        if not np.isin(labels, [0, 1]).all():
            raise DatasetAlignmentError(
                "Training labels must be binary"
            )

        if len(np.unique(labels)) != 2:
            raise DatasetAlignmentError(
                "Training dataset must contain both relevance classes"
            )

        return ordered_rows, labels

    def _split_dataset(
        self,
        rows: Sequence[RecommendationFeatureRow],
        labels: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:

        groups = np.asarray(
            [str(row.user_id) for row in rows]
        )

        unique_users = np.unique(groups)

        if len(unique_users) < 4:
            raise DatasetSplitError(
                "At least four distinct users are required "
                "for a meaningful user-separated split."
            )

        splitter = GroupShuffleSplit(
            n_splits=self.config.max_split_attempts,
            test_size=self.config.validation_size,
            random_state=self.config.random_state,
        )

        for train_indices, validation_indices in splitter.split(
            np.zeros(len(rows)),
            labels,
            groups,
        ):
            train_labels = labels[train_indices]
            validation_labels = labels[validation_indices]

            if len(train_indices) < self.config.min_training_samples:
                continue

            if len(validation_indices) < self.config.min_validation_samples:
                continue

            # Both partitions must contain both relevance classes.
            if len(np.unique(train_labels)) != 2:
                continue

            if len(np.unique(validation_labels)) != 2:
                continue

            train_users = set(groups[train_indices])
            validation_users = set(groups[validation_indices])

            if train_users.intersection(validation_users):
                continue

            return train_indices, validation_indices

        raise DatasetSplitError(
            "Unable to produce a valid user-separated split "
            "containing both relevance classes in both partitions. "
            "The dataset may be too small or class distribution "
            "may be concentrated in too few users."
        )

    def train(
        self,
        feature_rows: Sequence[RecommendationFeatureRow],
        examples: Sequence[RecommendationTrainingExample],
    ) -> TrainingResult:
        """
        Execute a complete reproducible training run.

        The feature transformer is fitted only on training data.
        Validation data is transformed without refitting.
        """

        rows, labels = self._validate_inputs(
            feature_rows,
            examples,
        )

        train_indices, validation_indices = self._split_dataset(
            rows,
            labels,
        )

        train_rows = [
            rows[index]
            for index in train_indices
        ]

        validation_rows = [
            rows[index]
            for index in validation_indices
        ]

        train_labels = labels[train_indices]
        validation_labels = labels[validation_indices]

        # Align examples with feature rows using their grouping keys.
        example_map = {
            example.sample_key: example
            for example in examples
        }

        train_weights = np.asarray(
            [
                example_map[row.grouping_key].confidence
                for row in train_rows
            ],
            dtype=np.float64,
        )

        # Convert training rows to model-facing records.
        train_records = [
            row.to_model_features()
            for row in train_rows
        ]

        validation_records = [
            row.to_model_features()
            for row in validation_rows
        ]

        # Fit transformations exclusively on training data.
        train_transformation = (
            self.feature_transformer.fit_transform(
                train_records
            )
        )

        validation_transformation = (
            self.feature_transformer.transform(
                validation_records
            )
        )

        feature_names = train_transformation.feature_names

        if (
            train_transformation.feature_count
            != validation_transformation.feature_count
        ):
            raise TrainingPipelineError(
                "Training and validation feature dimensions differ"
            )

        training_summary = self.model.fit(
            train_transformation.matrix,
            train_labels,
            feature_names=feature_names,
            sample_weight=train_weights,
        )

        self.dummy_baseline.fit(
            train_transformation.matrix,
            train_labels,
        )

        training_statistics = self._statistics(
            train_rows,
            train_labels,
        )

        validation_statistics = self._statistics(
            validation_rows,
            validation_labels,
        )

        evaluation_dataset = EvaluationDataset(
            X=validation_transformation.matrix,
            y=validation_labels.copy(),
            user_ids=tuple(
                row.user_id
                for row in validation_rows
            ),
            resource_ids=tuple(
                row.resource_id
                for row in validation_rows
            ),
            statistics=validation_statistics,
        )

        # Record distinct users in each partition for auditability.
        training_user_ids = tuple(
            sorted(
                {row.user_id for row in train_rows},
                key=str,
            )
        )

        validation_user_ids = tuple(
            sorted(
                {row.user_id for row in validation_rows},
                key=str,
            )
        )

        trained_at = datetime.now(timezone.utc)

        return TrainingResult(
            run_id=(
                f"scholarai-ml-"
                f"{trained_at.strftime('%Y%m%dT%H%M%S%fZ')}"
            ),
            trained_at=trained_at,
            model=self.model,
            dummy_baseline=self.dummy_baseline,
            feature_transformer=self.feature_transformer,
            training_summary=training_summary,
            training_statistics=training_statistics,
            validation_statistics=validation_statistics,
            feature_names=feature_names,
            training_user_ids=training_user_ids,
            validation_user_ids=validation_user_ids,
            training_class_distribution=self._class_distribution(
                train_labels
            ),
            validation_class_distribution=self._class_distribution(
                validation_labels
            ),
            evaluation_dataset=evaluation_dataset,
            config=self.config,
        )