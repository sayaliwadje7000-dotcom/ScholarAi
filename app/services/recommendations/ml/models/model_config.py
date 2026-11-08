"""Configuration for ScholarAI recommendation baseline models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaselineModelConfig:
    """Configuration for the Logistic Regression baseline."""

    regularization_strength: float = 1.0

    max_iterations: int = 1000

    tolerance: float = 1e-4

    class_weight: str | None = "balanced"

    random_state: int = 42

    solver: str = "lbfgs"

    def __post_init__(self) -> None:

        if self.regularization_strength <= 0:
            raise ValueError(
                "regularization_strength must be positive"
            )

        if self.max_iterations < 1:
            raise ValueError(
                "max_iterations must be positive"
            )

        if self.tolerance <= 0:
            raise ValueError(
                "tolerance must be positive"
            )

        if self.solver not in {"lbfgs", "liblinear"}:
            raise ValueError(
                "Unsupported Logistic Regression solver"
            )

        if self.class_weight not in {
            None,
            "balanced",
        }:
            raise ValueError(
                "class_weight must be None or 'balanced'"
            )