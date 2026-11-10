import pytest

from app.evaluation.optimization.exceptions import (
    CandidateEvaluationError,
    OptimizationValidationError,
)
from app.evaluation.optimization.runner import OptimizationRunner
from app.evaluation.optimization.schemas import (
    OptimizationCandidate,
    OptimizationConfig,
)


def make_config():
    return OptimizationConfig(
        optimization_id="runner-test",
        baseline_candidate=OptimizationCandidate(
            candidate_id="baseline",
            parameters={"temperature": 0.7},
        ),
        candidates=[
            OptimizationCandidate(
                candidate_id="candidate-1",
                parameters={"temperature": 0.2},
            ),
            OptimizationCandidate(
                candidate_id="candidate-2",
                parameters={"temperature": 0.4},
            ),
        ],
        objective_metric="quality",
        minimum_improvement=0.05,
        minimum_samples=2,
        guardrail_limits={"latency": 2.0},
    )


def evaluator(candidate):
    if candidate.candidate_id == "baseline":
        return {
            "quality": [0.70, 0.72],
            "latency": [1.0, 1.1],
        }

    if candidate.candidate_id == "candidate-1":
        return {
            "quality": [0.90, 0.92],
            "latency": [1.2, 1.3],
        }

    return {
        "quality": [0.80, 0.82],
        "latency": [1.1, 1.2],
    }


def test_runner_selects_best_accepted_candidate():
    runner = OptimizationRunner(make_config(), evaluator)

    report = runner.run()

    assert report.completed is True
    assert report.passed is True
    assert report.selected_candidate_id == "candidate-1"
    assert report.selected_score == pytest.approx(0.91)
    assert report.baseline_score == pytest.approx(0.71)
    assert report.improvement == pytest.approx(0.20)


def test_runner_returns_failure_when_no_candidate_passes():
    config = make_config()
    config.minimum_improvement = 1.0

    report = OptimizationRunner(config, evaluator).run()

    assert report.completed is True
    assert report.passed is False
    assert report.selected_candidate_id is None


def test_runner_rejects_missing_objective_metric():
    def invalid_evaluator(candidate):
        return {"latency": [1.0, 1.1]}

    runner = OptimizationRunner(make_config(), invalid_evaluator)

    with pytest.raises(OptimizationValidationError):
        runner.run()


def test_runner_wraps_evaluator_exception():
    def failing_evaluator(candidate):
        raise RuntimeError("Evaluation service unavailable")

    runner = OptimizationRunner(make_config(), failing_evaluator)

    with pytest.raises(CandidateEvaluationError):
        runner.run()


def test_runner_rejects_invalid_evaluator_output():
    def invalid_evaluator(candidate):
        return ["not", "a", "dictionary"]

    runner = OptimizationRunner(make_config(), invalid_evaluator)

    with pytest.raises(OptimizationValidationError):
        runner.run()
