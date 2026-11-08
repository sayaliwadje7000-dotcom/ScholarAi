"""Configuration for ScholarAI ML experiment tracking."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExperimentTrackingConfig:
    """Configuration for experiment metadata storage."""

    storage_directory: Path = Path(
        "artifacts/recommendation_experiments"
    )

    schema_version: str = "1.0"

    include_environment_metadata: bool = True

    include_dataset_fingerprint: bool = True

    allow_overwrite: bool = False

    def __post_init__(self) -> None:

        if not isinstance(self.storage_directory, Path):
            object.__setattr__(
                self,
                "storage_directory",
                Path(self.storage_directory),
            )

        if not self.schema_version.strip():
            raise ValueError(
                "Experiment schema version cannot be empty."
            )

        if self.storage_directory.exists() and not (
            self.storage_directory.is_dir()
        ):
            raise ValueError(
                "Experiment storage path must be a directory."
            )