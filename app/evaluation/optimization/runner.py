from collections.abc import Callable

from app.evaluation.optimization.exceptions import (
    CandidateEvaluationError,
    OptimizationExecutionError,
    OptimizationValidationError,
)
from app.evaluation.optimization.results import (
    summarize_metrics,
    validate_metric_values,
)
from app.evaluation.optimization.schemas import (
    CandidateEvaluation,
    OptimizationCandidate,
    OptimizationConfig,
    OptimizationReport,
)
from app.evaluation.optimization.validation import compare_candidate


Evaluator = Callable[
    [OptimizationCandidate],
    dict[str, list[float]],
]


class OptimizationRunner:
    """Run baseline and candidate evaluations."""

    def __init__(
        self,
        config: OptimizationConfig,
        evaluator: Evaluator,
    ):
        if not callable(evaluator):
            raise OptimizationExecutionError(
                "Evaluator must be callable."
            )

        self.config = config
        self.evaluator = evaluator

    def _evaluate(
        self,
        candidate: OptimizationCandidate,
    ) -> CandidateEvaluation:
        try:
            metric_values = self.evaluator(candidate)

            if not isinstance(metric_values, dict):
                raise OptimizationValidationError(
                    "Evaluator must return a metric-to-values dictionary."
                )

            validate_metric_values(
                metric_values,
                self.config.minimum_samples,
            )

            means, deviations, counts = summarize_metrics(metric_values)

            return CandidateEvaluation(
                candidate_id=candidate.candidate_id,
                parameters=candidate.parameters,
                metric_values=metric_values,
                metric_means=means,
                metric_standard_deviations=deviations,
                sample_counts=counts,
            )

        except OptimizationValidationError:
            raise

        except Exception as exc:
            raise CandidateEvaluationError(
                f"Evaluation failed for candidate "
                f"'{candidate.candidate_id}': {exc}"
            ) from exc

    def run(self) -> OptimizationReport:
        try:
            baseline = self._evaluate(
                self.config.baseline_candidate
            )

            objective = self.config.objective_metric

            if objective not in baseline.metric_means:
                raise OptimizationValidationError(
                    f"Baseline does not contain objective metric '{objective}'."
                )

            evaluations = []

            for candidate in self.config.candidates:
                evaluation = self._evaluate(candidate)

                evaluation = compare_candidate(
                    evaluation,
                    baseline,
                    self.config,
                )

                evaluations.append(evaluation)

            accepted = [
                item for item in evaluations if item.accepted
            ]

            if accepted:
                if self.config.higher_is_better:
                    selected = max(
                        accepted,
                        key=lambda item: item.objective_score,
                    )
                else:
                    selected = min(
                        accepted,
                        key=lambda item: item.objective_score,
                    )

                selected_id = selected.candidate_id
                selected_parameters = selected.parameters
                selected_score = selected.objective_score

                baseline_score = baseline.metric_means[objective]

                improvement = (
                    selected_score - baseline_score
                    if self.config.higher_is_better
                    else baseline_score - selected_score
                )

                passed = True

                summary = (
                    f"Optimization completed. Candidate '{selected_id}' "
                    f"was selected with an improvement of {improvement:.6f}."
                )

            else:
                selected_id = None
                selected_parameters = None
                selected_score = None
                improvement = None
                passed = False

                summary = (
                    "Optimization completed, but no candidate satisfied "
                    "all improvement and quality guardrails."
                )

            return OptimizationReport(
                optimization_id=self.config.optimization_id,
                baseline=baseline,
                evaluations=evaluations,
                selected_candidate_id=selected_id,
                selected_parameters=selected_parameters,
                baseline_score=baseline.metric_means[objective],
                selected_score=selected_score,
                improvement=improvement,
                completed=True,
                passed=passed,
                summary=summary,
            )

        except (
            CandidateEvaluationError,
            OptimizationValidationError,
        ):
            raise

        except Exception as exc:
            raise OptimizationExecutionError(
                f"Optimization run failed: {exc}"
            ) from exc
