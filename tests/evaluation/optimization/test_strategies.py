import pytest

from app.evaluation.optimization.exceptions import (
    OptimizationConfigurationError,
)
from app.evaluation.optimization.strategies import generate_candidates


def test_generate_grid_candidates():
    candidates = generate_candidates(
        {
            "temperature": [0.1, 0.5],
            "top_p": [0.8, 1.0],
        }
    )

    assert len(candidates) == 4
    assert candidates[0].candidate_id == "candidate_1"
    assert candidates[0].parameters == {
        "temperature": 0.1,
        "top_p": 0.8,
    }


def test_candidate_generation_is_deterministic():
    parameter_space = {
        "temperature": [0.1, 0.5],
    }

    first = generate_candidates(parameter_space)
    second = generate_candidates(parameter_space)

    assert [item.model_dump() for item in first] == [
        item.model_dump() for item in second
    ]


def test_empty_parameter_space_rejected():
    with pytest.raises(OptimizationConfigurationError):
        generate_candidates({})


def test_empty_parameter_values_rejected():
    with pytest.raises(OptimizationConfigurationError):
        generate_candidates({"temperature": []})


def test_maximum_candidate_limit_enforced():
    with pytest.raises(OptimizationConfigurationError):
        generate_candidates(
            {"temperature": [0.1, 0.2, 0.3]},
            maximum_candidates=2,
        )
