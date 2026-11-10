from app.evaluation.optimization.schemas import (
    CandidateEvaluation,
    OptimizationCandidate,
    OptimizationConfig,
)
from app.evaluation.optimization.validation import compare_candidate


def make_config(**kwargs):
    values = {
        "optimization_id": "test",
        "baseline_candidate": OptimizationCandidate(
            candidate_id="baseline"
        ),
        "candidates": [
            OptimizationCandidate(candidate_id="candidate")
        ],
        "objective_metric": "quality",
    }
    values.update(kwargs)
    return OptimizationConfig(**values)


def make_evaluation(candidate_id, metrics):
    return CandidateEvaluation(
        candidate_id=candidate_id,
        metric_means=metrics,
    )


def test_candidate_with_improvement_is_accepted():
    config = make_config(minimum_improvement=0.05)

    baseline = make_evaluation("baseline", {"quality": 0.7})
    candidate = make_evaluation("candidate", {"quality": 0.8})

    result = compare_candidate(candidate, baseline, config)

    assert result.accepted is True
    assert result.objective_score == 0.8


def test_candidate_without_required_improvement_is_rejected():
    config = make_config(minimum_improvement=0.2)

    baseline = make_evaluation("baseline", {"quality": 0.7})
    candidate = make_evaluation("candidate", {"quality": 0.8})

    result = compare_candidate(candidate, baseline, config)

    assert result.accepted is False
    assert result.violations


def test_guardrail_rejects_latency_regression():
    config = make_config(
        guardrail_limits={"latency": 2.0},
        guardrails_higher_is_better={"latency": False},
    )

    baseline = make_evaluation(
        "baseline",
        {"quality": 0.7, "latency": 1.0},
    )
    candidate = make_evaluation(
        "candidate",
        {"quality": 0.9, "latency": 3.0},
    )

    result = compare_candidate(candidate, baseline, config)

    assert result.accepted is False
    assert any("latency" in item for item in result.violations)


def test_missing_guardrail_metric_rejected():
    config = make_config(
        guardrail_limits={"latency": 2.0},
    )

    baseline = make_evaluation("baseline", {"quality": 0.7})
    candidate = make_evaluation("candidate", {"quality": 0.9})

    result = compare_candidate(candidate, baseline, config)

    assert result.accepted is False


def test_lower_is_better_objective():
    config = make_config(
        objective_metric="latency",
        higher_is_better=False,
        minimum_improvement=0.1,
    )

    baseline = make_evaluation("baseline", {"latency": 2.0})
    candidate = make_evaluation("candidate", {"latency": 1.5})

    result = compare_candidate(candidate, baseline, config)

    assert result.accepted is True
