import pytest
from pydantic import ValidationError

from app.evaluation.optimization.schemas import (
    OptimizationCandidate,
    OptimizationConfig,
)


def make_candidate(candidate_id):
    return OptimizationCandidate(
        candidate_id=candidate_id,
        parameters={"temperature": 0.2},
    )


def test_valid_optimization_config():
    config = OptimizationConfig(
        optimization_id="experiment-1",
        baseline_candidate=make_candidate("baseline"),
        candidates=[make_candidate("candidate-1")],
        objective_metric="quality",
    )

    assert config.optimization_id == "experiment-1"


def test_duplicate_candidate_ids_rejected():
    with pytest.raises(ValidationError):
        OptimizationConfig(
            optimization_id="experiment-1",
            baseline_candidate=make_candidate("baseline"),
            candidates=[
                make_candidate("candidate-1"),
                make_candidate("candidate-1"),
            ],
            objective_metric="quality",
        )


def test_baseline_cannot_be_candidate():
    with pytest.raises(ValidationError):
        OptimizationConfig(
            optimization_id="experiment-1",
            baseline_candidate=make_candidate("baseline"),
            candidates=[make_candidate("baseline")],
            objective_metric="quality",
        )


def test_guardrail_direction_requires_limit():
    with pytest.raises(ValidationError):
        OptimizationConfig(
            optimization_id="experiment-1",
            baseline_candidate=make_candidate("baseline"),
            candidates=[make_candidate("candidate-1")],
            objective_metric="quality",
            guardrails_higher_is_better={"latency": False},
        )
