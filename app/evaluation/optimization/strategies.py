from itertools import product
from typing import Any

from app.evaluation.optimization.exceptions import (
    OptimizationConfigurationError,
)
from app.evaluation.optimization.schemas import OptimizationCandidate


def generate_candidates(
    parameter_space: dict[str, list[Any]],
    prefix: str = "candidate",
    maximum_candidates: int = 100,
) -> list[OptimizationCandidate]:
    """Generate deterministic grid-search candidates."""

    if not parameter_space:
        raise OptimizationConfigurationError(
            "Parameter space cannot be empty."
        )

    if maximum_candidates < 1:
        raise OptimizationConfigurationError(
            "maximum_candidates must be at least 1."
        )

    keys = list(parameter_space.keys())

    for key, values in parameter_space.items():
        if not isinstance(key, str) or not key.strip():
            raise OptimizationConfigurationError(
                "Parameter names must be non-empty strings."
            )

        if not isinstance(values, list) or not values:
            raise OptimizationConfigurationError(
                f"Parameter '{key}' must contain a non-empty list."
            )

    candidate_count = 1

    for values in parameter_space.values():
        candidate_count *= len(values)

    if candidate_count > maximum_candidates:
        raise OptimizationConfigurationError(
            f"Grid contains {candidate_count} candidates; "
            f"maximum allowed is {maximum_candidates}."
        )

    candidates = []

    combinations = product(
        *(parameter_space[key] for key in keys)
    )

    for index, combination in enumerate(combinations, start=1):
        candidates.append(
            OptimizationCandidate(
                candidate_id=f"{prefix}_{index}",
                parameters=dict(zip(keys, combination)),
            )
        )

    return candidates
