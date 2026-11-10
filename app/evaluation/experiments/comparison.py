from app.evaluation.experiments.schemas import (
    ExperimentConfig,
    ExperimentComparisonReport,
    ExperimentObservation,
    VariantStatistics,
)
from app.evaluation.experiments.statistics import (
    bootstrap_mean_difference,
    mean,
    median,
    normal_two_sided_p_value,
    paired_effect_size,
    standard_deviation,
    standard_error,
)
from app.evaluation.experiments.validation import validate_observations


def _variant_statistics(
    variant: str,
    observations: list[ExperimentObservation],
) -> VariantStatistics:
    values = [item.value for item in observations]

    return VariantStatistics(
        variant=variant,
        sample_count=len(values),
        mean=mean(values),
        median=median(values),
        standard_deviation=standard_deviation(values),
        standard_error=standard_error(values),
        minimum=min(values),
        maximum=max(values),
    )


def compare_experiment(
    config: ExperimentConfig,
    observations: list[ExperimentObservation],
) -> ExperimentComparisonReport:
    grouped = validate_observations(config, observations)

    baseline = grouped[config.baseline_variant]
    candidate = grouped[config.candidate_variant]

    baseline_by_id = {
        item.sample_id: item.value
        for item in baseline
    }

    candidate_by_id = {
        item.sample_id: item.value
        for item in candidate
    }

    sample_ids = sorted(baseline_by_id)

    differences = [
        candidate_by_id[sample_id] - baseline_by_id[sample_id]
        for sample_id in sample_ids
    ]

    difference_mean = mean(differences)
    difference_error = standard_error(differences)

    confidence_lower, confidence_upper = bootstrap_mean_difference(
        differences=differences,
        iterations=config.bootstrap_iterations,
        confidence_level=1 - config.alpha,
        random_seed=config.random_seed,
    )

    p_value = normal_two_sided_p_value(
        difference_mean,
        difference_error,
    )

    statistically_significant = p_value < config.alpha

    directionally_favorable = (
        difference_mean > 0
        if config.higher_is_better
        else difference_mean < 0
    )

    practical_significance = (
        abs(difference_mean) >= config.minimum_effect_size
    )

    winner = None

    if statistically_significant and directionally_favorable:
        winner = config.candidate_variant
    elif statistically_significant and not directionally_favorable:
        winner = config.baseline_variant

    passed = (
        statistically_significant
        and directionally_favorable
        and practical_significance
    )

    violations = []

    if not statistically_significant:
        violations.append("statistical_significance_not_established")

    if not directionally_favorable:
        violations.append("candidate_direction_not_favorable")

    if not practical_significance:
        violations.append("minimum_practical_effect_not_met")

    return ExperimentComparisonReport(
        experiment_id=config.experiment_id,
        metric_name=config.metric_name,
        baseline_variant=config.baseline_variant,
        candidate_variant=config.candidate_variant,
        baseline_statistics=_variant_statistics(
            config.baseline_variant,
            baseline,
        ),
        candidate_statistics=_variant_statistics(
            config.candidate_variant,
            candidate,
        ),
        paired_sample_count=len(differences),
        mean_difference=difference_mean,
        confidence_interval_lower=confidence_lower,
        confidence_interval_upper=confidence_upper,
        p_value=p_value,
        alpha=config.alpha,
        effect_size=paired_effect_size(differences),
        statistically_significant=statistically_significant,
        practical_significance=practical_significance,
        winner=winner,
        passed=passed,
        higher_is_better=config.higher_is_better,
        bootstrap_iterations=config.bootstrap_iterations,
        violations=violations,
    )
