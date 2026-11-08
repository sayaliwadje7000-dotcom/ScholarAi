"""Persistent experiment tracking for ScholarAI recommendation models."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import tempfile

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

import numpy as np

from app.services.recommendations.ml.experiments.experiment_config import (
    ExperimentTrackingConfig,
)
from app.services.recommendations.ml.experiments.experiment_record import (
    ExperimentRecord,
)
from app.services.recommendations.ml.privacy.data_sanitizer import (
    MetadataSanitizer,
)


class ExperimentTrackingError(Exception):
    """Base exception for experiment tracking failures."""


class InvalidExperimentRunError(ExperimentTrackingError):
    """Raised when an experiment run is invalid."""


class DuplicateExperimentRunError(ExperimentTrackingError):
    """Raised when an experiment run already exists."""


class ExperimentNotFoundError(ExperimentTrackingError):
    """Raised when an experiment cannot be found."""


class ExperimentSerializationError(ExperimentTrackingError):
    """Raised when experiment metadata cannot be serialized."""


class ExperimentStorageError(ExperimentTrackingError):
    """Raised when experiment metadata cannot be persisted."""


class RecommendationExperimentTracker:
    """Stores and retrieves recommendation-model experiment metadata."""

    RUN_ID_PATTERN = re.compile(
        r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"
    )

    def __init__(
        self,
        config: ExperimentTrackingConfig | None = None,
    ) -> None:
        self.config = config or ExperimentTrackingConfig()

        # Initialize the sanitizer before any tracking operation.
        self.metadata_sanitizer = MetadataSanitizer()

        self.storage_directory = self.config.storage_directory

        try:
            self.storage_directory.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as exc:
            raise ExperimentStorageError(
                "Unable to initialize experiment storage."
            ) from exc

    @classmethod
    def _validate_run_id(cls, run_id: str) -> str:
        if not isinstance(run_id, str):
            raise InvalidExperimentRunError(
                "Experiment run ID must be a string."
            )

        if not cls.RUN_ID_PATTERN.fullmatch(run_id):
            raise InvalidExperimentRunError(
                "Experiment run ID contains invalid characters "
                "or exceeds the permitted length."
            )

        return run_id

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Convert supported Python objects into JSON-safe values."""

        if value is None:
            return None

        if isinstance(value, Enum):
            return value.value

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, Path):
            return str(value)

        if isinstance(value, np.ndarray):
            return value.tolist()

        if isinstance(value, np.generic):
            return value.item()

        if is_dataclass(value) and not isinstance(value, type):
            return RecommendationExperimentTracker._json_safe(
                asdict(value)
            )

        if isinstance(value, Mapping):
            return {
                str(key): RecommendationExperimentTracker._json_safe(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                RecommendationExperimentTracker._json_safe(item)
                for item in value
            ]

        if isinstance(value, (str, int, float, bool)):
            return value

        raise ExperimentSerializationError(
            f"Unsupported metadata type: {type(value).__name__}"
        )

    @staticmethod
    def _statistics_to_dict(statistics: Any) -> dict[str, Any]:
        if is_dataclass(statistics) and not isinstance(
            statistics,
            type,
        ):
            result = asdict(statistics)

        elif isinstance(statistics, Mapping):
            result = dict(statistics)

        else:
            raise ExperimentSerializationError(
                "Dataset statistics must be a dataclass or mapping."
            )

        return RecommendationExperimentTracker._json_safe(result)

    @staticmethod
    def _configuration_to_dict(
        configuration: Any,
    ) -> dict[str, Any]:
        if is_dataclass(configuration) and not isinstance(
            configuration,
            type,
        ):
            result = asdict(configuration)

        elif isinstance(configuration, Mapping):
            result = dict(configuration)

        else:
            raise ExperimentSerializationError(
                "Training configuration must be a dataclass "
                "or mapping."
            )

        return RecommendationExperimentTracker._json_safe(result)

    @staticmethod
    def _environment_metadata() -> dict[str, Any]:
        packages = (
            "numpy",
            "scipy",
            "scikit-learn",
            "joblib",
        )

        package_versions = {}

        for package in packages:
            try:
                package_versions[package] = version(package)
            except PackageNotFoundError:
                package_versions[package] = None

        return {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "packages": package_versions,
        }

    @staticmethod
    def _dataset_fingerprint(
        evaluation_dataset: Any,
        feature_names: tuple[str, ...],
    ) -> str:
        """
        Create a privacy-conscious metadata fingerprint.

        User IDs and resource IDs are deliberately excluded.

        This fingerprint uses validation labels, matrix shape,
        and feature names. It is not a fingerprint of the full
        underlying feature values.
        """
        labels = np.asarray(
            evaluation_dataset.y,
            dtype=np.int64,
        )

        matrix = evaluation_dataset.X
        shape = getattr(matrix, "shape", None)

        if shape is None:
            raise ExperimentSerializationError(
                "Evaluation feature matrix has no shape."
            )

        fingerprint_payload = {
            "labels": labels.tolist(),
            "matrix_shape": list(shape),
            "feature_names": list(feature_names),
        }

        serialized = json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

        return hashlib.sha256(serialized).hexdigest()

    @staticmethod
    def _evaluation_report_to_dict(
        evaluation_report: Any,
    ) -> dict[str, Any]:
        if not callable(
            getattr(evaluation_report, "to_dict", None)
        ):
            raise ExperimentSerializationError(
                "Evaluation report must provide a to_dict() method."
            )

        result = evaluation_report.to_dict()

        if not isinstance(result, Mapping):
            raise ExperimentSerializationError(
                "Evaluation report to_dict() must return a mapping."
            )

        return RecommendationExperimentTracker._json_safe(result)

    def _build_record(
        self,
        training_result: Any,
        evaluation_report: Any,
        tags: Mapping[str, str] | None,
        artifact_reference: str | None,
    ) -> ExperimentRecord:
        run_id = self._validate_run_id(training_result.run_id)

        if (
            getattr(evaluation_report, "run_id", run_id)
            != run_id
        ):
            raise InvalidExperimentRunError(
                "Training and evaluation run IDs do not match."
            )

        if tags is None:
            tags = {}

        if not isinstance(tags, Mapping):
            raise InvalidExperimentRunError(
                "Experiment tags must be a mapping."
            )

        normalized_tags = {}

        for key, value in tags.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise InvalidExperimentRunError(
                    "Experiment tag keys and values must be strings."
                )

            key = key.strip()
            value = value.strip()

            if not key or not value:
                raise InvalidExperimentRunError(
                    "Experiment tag keys and values cannot be empty."
                )

            normalized_tags[key] = self.metadata_sanitizer.sanitize(
                value
            )

        if artifact_reference is not None:
            if not isinstance(artifact_reference, str):
                raise InvalidExperimentRunError(
                    "Artifact reference must be a string."
                )

            artifact_reference = artifact_reference.strip()

            if not artifact_reference:
                raise InvalidExperimentRunError(
                    "Artifact reference cannot be empty."
                )

            artifact_reference = self.metadata_sanitizer.sanitize(
                artifact_reference
            )

        evaluation_dataset = training_result.evaluation_dataset

        feature_names = tuple(training_result.feature_names)

        fingerprint = None

        if self.config.include_dataset_fingerprint:
            fingerprint = self._dataset_fingerprint(
                evaluation_dataset,
                feature_names,
            )

        environment = {}

        if self.config.include_environment_metadata:
            environment = self._environment_metadata()

        model = training_result.model

        model_name = getattr(
            model,
            "model_name",
            type(model).__name__,
        )

        sanitized_evaluation_report = (
            self.metadata_sanitizer.sanitize(
                self._evaluation_report_to_dict(evaluation_report)
            )
        )

        return ExperimentRecord(
            schema_version=self.config.schema_version,
            run_id=run_id,
            recorded_at=datetime.now(timezone.utc),
            trained_at=training_result.trained_at,
            model_name=str(model_name),
            training_configuration=self._configuration_to_dict(
                training_result.config
            ),
            training_statistics=self._statistics_to_dict(
                training_result.training_statistics
            ),
            validation_statistics=self._statistics_to_dict(
                training_result.validation_statistics
            ),
            training_class_distribution=self._json_safe(
                training_result.training_class_distribution
            ),
            validation_class_distribution=self._json_safe(
                training_result.validation_class_distribution
            ),
            feature_names=feature_names,
            evaluation_report=sanitized_evaluation_report,
            environment=environment,
            dataset_fingerprint=fingerprint,
            tags=normalized_tags,
            artifact_reference=artifact_reference,
        )

    def _record_path(self, run_id: str) -> Path:
        run_id = self._validate_run_id(run_id)
        return self.storage_directory / f"{run_id}.json"

    def record_run(
        self,
        training_result: Any,
        evaluation_report: Any,
        tags: Mapping[str, str] | None = None,
        artifact_reference: str | None = None,
    ) -> ExperimentRecord:
        """
        Persist one completed training and evaluation experiment.

        The model artifact itself is not serialized here.
        Use the Phase 14.5 artifact store for model persistence.
        """
        record = self._build_record(
            training_result=training_result,
            evaluation_report=evaluation_report,
            tags=tags,
            artifact_reference=artifact_reference,
        )

        target_path = self._record_path(record.run_id)

        if (
            target_path.exists()
            and not self.config.allow_overwrite
        ):
            raise DuplicateExperimentRunError(
                f"Experiment run already exists: {record.run_id}"
            )

        lock_path = target_path.with_suffix(".lock")
        temporary_path = None
        lock_acquired = False

        try:
            # Exclusive creation prevents concurrent writers from
            # silently replacing the same experiment record.
            lock_descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            lock_acquired = True
            os.close(lock_descriptor)

            if (
                target_path.exists()
                and not self.config.allow_overwrite
            ):
                raise DuplicateExperimentRunError(
                    f"Experiment run already exists: {record.run_id}"
                )

            serialized = json.dumps(
                record.to_dict(),
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".tmp",
                prefix=f"{record.run_id}_",
                dir=self.storage_directory,
                delete=False,
            ) as temporary_file:
                temporary_file.write(serialized)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

                temporary_path = Path(temporary_file.name)

            os.replace(
                temporary_path,
                target_path,
            )
            temporary_path = None

            return record

        except DuplicateExperimentRunError:
            raise

        except FileExistsError as exc:
            raise ExperimentStorageError(
                "Another process is writing this experiment."
            ) from exc

        except (OSError, TypeError, ValueError) as exc:
            raise ExperimentStorageError(
                "Unable to persist experiment metadata."
            ) from exc

        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

            # Only remove a lock created by this process.
            if lock_acquired:
                lock_path.unlink(missing_ok=True)

    def get_run(self, run_id: str) -> dict[str, Any]:
        path = self._record_path(run_id)

        if not path.is_file():
            raise ExperimentNotFoundError(
                f"Experiment run not found: {run_id}"
            )

        try:
            with path.open("r", encoding="utf-8") as file:
                result = json.load(file)

        except (OSError, json.JSONDecodeError) as exc:
            raise ExperimentStorageError(
                f"Unable to read experiment run: {run_id}"
            ) from exc

        if result.get("run_id") != run_id:
            raise ExperimentStorageError(
                "Experiment metadata run ID does not match its filename."
            )

        return result

    def list_runs(self) -> list[dict[str, Any]]:
        """Return all stored experiment records."""

        records = []

        for path in self.storage_directory.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8") as file:
                    record = json.load(file)

                if record.get("run_id") != path.stem:
                    raise ExperimentStorageError(
                        "Experiment filename and run ID do not match."
                    )

                records.append(record)

            except (OSError, json.JSONDecodeError) as exc:
                raise ExperimentStorageError(
                    f"Unable to read experiment file: {path.name}"
                ) from exc

        records.sort(
            key=lambda item: item.get("recorded_at", ""),
            reverse=True,
        )

        return records