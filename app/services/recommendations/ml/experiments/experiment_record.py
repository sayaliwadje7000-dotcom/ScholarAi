"""Experiment metadata contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    """Immutable metadata for one recommendation-model experiment."""

    schema_version: str

    run_id: str

    recorded_at: datetime

    trained_at: datetime

    model_name: str

    training_configuration: dict[str, Any]

    training_statistics: dict[str, Any]

    validation_statistics: dict[str, Any]

    training_class_distribution: dict[str, int]

    validation_class_distribution: dict[str, int]

    feature_names: tuple[str, ...]

    evaluation_report: dict[str, Any]

    environment: dict[str, Any]

    dataset_fingerprint: str | None

    tags: dict[str, str]

    artifact_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:

        return {
            "schema_version": self.schema_version,

            "run_id": self.run_id,

            "recorded_at": self.recorded_at.isoformat(),

            "trained_at": self.trained_at.isoformat(),

            "model_name": self.model_name,

            "training_configuration": self.training_configuration,

            "training_statistics": self.training_statistics,

            "validation_statistics": self.validation_statistics,

            "training_class_distribution": (
                self.training_class_distribution
            ),

            "validation_class_distribution": (
                self.validation_class_distribution
            ),

            "feature_names": list(self.feature_names),

            "evaluation_report": self.evaluation_report,

            "environment": self.environment,

            "dataset_fingerprint": self.dataset_fingerprint,

            "tags": self.tags,

            "artifact_reference": self.artifact_reference,
        }