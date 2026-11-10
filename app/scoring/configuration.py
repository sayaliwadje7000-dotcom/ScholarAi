from dataclasses import dataclass
import math

from app.scoring.exceptions import ScoringConfigurationError


@dataclass(frozen=True)
class ScoringConfiguration:
    weights: dict[str, float]

    def __post_init__(self):
        if not self.weights:
            raise ScoringConfigurationError(
                "At least one scoring weight is required."
            )

        for name, weight in self.weights.items():
            if not name:
                raise ScoringConfigurationError(
                    "Weight names cannot be empty."
                )

            if isinstance(weight, bool):
                raise ScoringConfigurationError(
                    "Weights must be numeric."
                )

            if not isinstance(weight, (int, float)):
                raise ScoringConfigurationError(
                    f"Weight '{name}' must be numeric."
                )

            if not math.isfinite(weight) or weight < 0:
                raise ScoringConfigurationError(
                    f"Weight '{name}' must be finite and non-negative."
                )

        if sum(self.weights.values()) <= 0:
            raise ScoringConfigurationError(
                "At least one weight must be positive."
            )

    def normalized_weights(self) -> dict[str, float]:
        total = sum(self.weights.values())

        return {
            name: weight / total
            for name, weight in self.weights.items()
        }