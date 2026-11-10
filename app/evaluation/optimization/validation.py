from app.evaluation.optimization.schemas import (
    CandidateEvaluation,
    OptimizationConfig,
)


def compare_candidate(
    evaluation: CandidateEvaluation,
    baseline: CandidateEvaluation,
    config: OptimizationConfig,
) -> CandidateEvaluation:
    """Compare a candidate against the baseline and enforce guardrails."""

    violations = []
    objective = config.objective_metric

    if objective not in evaluation.metric_means:
        violations.append(f"Missing objective metric: {objective}")

    if objective not in baseline.metric_means:
        violations.append(
            f"Baseline is missing objective metric: {objective}"
        )

    if violations:
        evaluation.eligible = False
        evaluation.accepted = False
        evaluation.violations = violations
        return evaluation

    candidate_score = evaluation.metric_means[objective]
    baseline_score = baseline.metric_means[objective]

    evaluation.objective_score = candidate_score

    for metric, limit in config.guardrail_limits.items():
        if metric not in evaluation.metric_means:
            violations.append(f"Missing guardrail metric: {metric}")
            continue

        candidate_value = evaluation.metric_means[metric]
        higher_is_better = config.guardrails_higher_is_better.get(
            metric,
            False,
        )

        if higher_is_better and candidate_value < limit:
            violations.append(
                f"Guardrail '{metric}' fell below minimum {limit}."
            )

        elif not higher_is_better and candidate_value > limit:
            violations.append(
                f"Guardrail '{metric}' exceeded maximum {limit}."
            )

    improvement = (
        candidate_score - baseline_score
        if config.higher_is_better
        else baseline_score - candidate_score
    )

    if improvement < config.minimum_improvement:
        violations.append(
            "Candidate did not achieve the required minimum improvement."
        )

    evaluation.eligible = True
    evaluation.violations = violations
    evaluation.accepted = len(violations) == 0

    return evaluation
