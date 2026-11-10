from collections import defaultdict

from app.evaluation.experiments.exceptions import (
    ExperimentValidationError,
)
from app.evaluation.experiments.schemas import (
    ExperimentConfig,
    ExperimentObservation,
)


def validate_observations(
    config: ExperimentConfig,
    observations: list[ExperimentObservation],
) -> dict[str, list[ExperimentObservation]]:
    if not observations:
        raise ExperimentValidationError(
            "Experiment contains no observations."
        )

    grouped = defaultdict(list)
    seen = set()

    for observation in observations:
        if observation.experiment_id != config.experiment_id:
            raise ExperimentValidationError(
                "Observation belongs to a different experiment."
            )

        if observation.metric_name != config.metric_name:
            raise ExperimentValidationError(
                "Observation metric does not match experiment metric."
            )

        if observation.variant not in {
            config.baseline_variant,
            config.candidate_variant,
        }:
            raise ExperimentValidationError(
                f"Unexpected experiment variant: {observation.variant}"
            )

        key = (observation.variant, observation.sample_id)

        if key in seen:
            raise ExperimentValidationError(
                f"Duplicate sample '{observation.sample_id}' "
                f"for variant '{observation.variant}'."
            )

        seen.add(key)
        grouped[observation.variant].append(observation)

    baseline = grouped[config.baseline_variant]
    candidate = grouped[config.candidate_variant]

    if len(baseline) < config.minimum_samples_per_variant:
        raise ExperimentValidationError(
            "Baseline variant has fewer than the required observations."
        )

    if len(candidate) < config.minimum_samples_per_variant:
        raise ExperimentValidationError(
            "Candidate variant has fewer than the required observations."
        )

    baseline_ids = {item.sample_id for item in baseline}
    candidate_ids = {item.sample_id for item in candidate}

    if baseline_ids != candidate_ids:
        raise ExperimentValidationError(
            "Paired experiment requires matching sample IDs "
            "for both variants."
        )

    return dict(grouped)
