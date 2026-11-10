from threading import RLock
from datetime import datetime, timezone

from app.evaluation.experiments.exceptions import (
    DuplicateExperimentError,
    ExperimentNotFoundError,
)
from app.evaluation.experiments.schemas import (
    ExperimentConfig,
    ExperimentObservation,
    ExperimentRecord,
)


class ExperimentRegistry:
    def __init__(self):
        self._experiments: dict[str, ExperimentRecord] = {}
        self._lock = RLock()

    def create(
        self,
        config: ExperimentConfig,
    ) -> ExperimentRecord:
        with self._lock:
            if config.experiment_id in self._experiments:
                raise DuplicateExperimentError(
                    f"Experiment '{config.experiment_id}' already exists."
                )

            record = ExperimentRecord(
                experiment_id=config.experiment_id,
                config=config,
            )

            self._experiments[config.experiment_id] = record

            return record.model_copy(deep=True)

    def get(self, experiment_id: str) -> ExperimentRecord:
        with self._lock:
            record = self._experiments.get(experiment_id)

            if record is None:
                raise ExperimentNotFoundError(
                    f"Experiment '{experiment_id}' was not found."
                )

            return record.model_copy(deep=True)

    def list_all(self) -> list[ExperimentRecord]:
        with self._lock:
            return [
                record.model_copy(deep=True)
                for record in self._experiments.values()
            ]

    def add_observation(
        self,
        experiment_id: str,
        observation: ExperimentObservation,
    ) -> ExperimentRecord:
        with self._lock:
            record = self._experiments.get(experiment_id)

            if record is None:
                raise ExperimentNotFoundError(
                    f"Experiment '{experiment_id}' was not found."
                )

            if record.status != "created":
                raise ValueError(
                    "Observations cannot be added after experiment completion."
                )

            if observation.experiment_id != experiment_id:
                raise ValueError(
                    "Observation experiment ID does not match registry ID."
                )

            existing = {
                (item.variant, item.sample_id)
                for item in record.observations
            }

            key = (observation.variant, observation.sample_id)

            if key in existing:
                raise ValueError(
                    "Duplicate observation for variant and sample."
                )

            updated = record.model_copy(deep=True)
            updated.observations.append(observation)

            self._experiments[experiment_id] = updated

            return updated.model_copy(deep=True)

    def complete(
        self,
        experiment_id: str,
    ) -> ExperimentRecord:
        with self._lock:
            record = self._experiments.get(experiment_id)

            if record is None:
                raise ExperimentNotFoundError(
                    f"Experiment '{experiment_id}' was not found."
                )

            if record.status == "completed":
                return record.model_copy(deep=True)

            updated = record.model_copy(deep=True)
            updated.status = "completed"
            updated.completed_at = datetime.now(timezone.utc)

            self._experiments[experiment_id] = updated

            return updated.model_copy(deep=True)

    def delete(self, experiment_id: str) -> None:
        with self._lock:
            if experiment_id not in self._experiments:
                raise ExperimentNotFoundError(
                    f"Experiment '{experiment_id}' was not found."
                )

            del self._experiments[experiment_id]

    def __len__(self) -> int:
        with self._lock:
            return len(self._experiments)
