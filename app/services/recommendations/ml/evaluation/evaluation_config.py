"""Configuration for recommendation model evaluation."""

from dataclasses import dataclass


class EvaluationConfigurationError(ValueError):
    """Raised when evaluation configuration is invalid."""


@dataclass(frozen=True, slots=True)
class EvaluationConfig:
    """Controls classification and ranking evaluation."""

    classification_threshold: float = 0.50

    ranking_k_values: tuple[int, ...] = (3, 5, 10)

    positive_label: int = 1
    negative_label: int = 0

    def __post_init__(self) -> None:

        if not 0.0 < self.classification_threshold < 1.0:
            raise EvaluationConfigurationError(
                "Classification threshold must be between 0 and 1."
            )

        if not self.ranking_k_values:
            raise EvaluationConfigurationError(
                "At least one ranking K value is required."
            )

        if any(
            not isinstance(k, int) or isinstance(k, bool) or k < 1
            for k in self.ranking_k_values
        ):
            raise EvaluationConfigurationError(
                "Ranking K values must be positive integers."
            )

        if len(set(self.ranking_k_values)) != len(
            self.ranking_k_values
        ):
            raise EvaluationConfigurationError(
                "Ranking K values must be unique."
            )

        if self.positive_label == self.negative_label:
            raise EvaluationConfigurationError(
                "Positive and negative labels must differ."
            )

        if {self.positive_label, self.negative_label} != {0, 1}:
            raise EvaluationConfigurationError(
                "This evaluator requires binary labels 0 and 1."
            )