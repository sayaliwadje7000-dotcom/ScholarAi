from app.evaluation.experiments.comparison import compare_experiment
from app.evaluation.experiments.exceptions import (
    ExperimentComparisonError,
)
from app.evaluation.experiments.registry import ExperimentRegistry
from app.evaluation.experiments.schemas import (
    ExperimentComparisonReport,
    ExperimentConfig,
    ExperimentObservation,
    ExperimentRecord,
)


class ExperimentRunner:
    def __init__(
        self,
        registry: ExperimentRegistry | None = None,
    ):
        self.registry = registry or ExperimentRegistry()

    def create_experiment(
        self,
        config: ExperimentConfig,
    ) -> ExperimentRecord:
        return self.registry.create(config)

    def record_observation(
        self,
        experiment_id: str,
        observation: ExperimentObservation,
    ) -> ExperimentRecord:
        return self.registry.add_observation(
            experiment_id,
            observation,
        )

    def run(
        self,
        experiment_id: str,
    ) -> ExperimentComparisonReport:
        record = self.registry.get(experiment_id)

        if record.status != "created":
            raise ExperimentComparisonError(
                "Only experiments in created status can be evaluated."
            )

        try:
            report = compare_experiment(
                config=record.config,
                observations=record.observations,
            )
        except Exception as exc:
            raise ExperimentComparisonError(
                f"Experiment evaluation failed: {exc}"
            ) from exc

        self.registry.complete(experiment_id)

        return report

    def get_experiment(
        self,
        experiment_id: str,
    ) -> ExperimentRecord:
        return self.registry.get(experiment_id)

    def list_experiments(self) -> list[ExperimentRecord]:
        return self.registry.list_all()
