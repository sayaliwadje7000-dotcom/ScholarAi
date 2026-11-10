from abc import ABC, abstractmethod
from typing import Any

from app.scoring.schemas import ScoreResult, ScoreComponent
from app.scoring.configuration import ScoringConfiguration
from app.scoring.normalization import normalize_score


class BaseScorer(ABC):
    name: str

    def __init__(self, configuration: ScoringConfiguration):
        self.configuration = configuration

    @abstractmethod
    def calculate_components(
        self,
        data: dict[str, Any],
    ) -> dict[str, float]:
        raise NotImplementedError

    def score(self, data: dict[str, Any]) -> ScoreResult:
        if not isinstance(data, dict):
            raise ValueError("Scoring input must be a dictionary.")

        raw_components = self.calculate_components(data)
        weights = self.configuration.normalized_weights()

        if set(raw_components) != set(weights):
            raise ValueError(
                "Calculated components must match configured weights."
            )

        components = []
        total = 0.0

        for name, weight in weights.items():
            value = normalize_score(raw_components[name])
            contribution = value * weight

            components.append(
                ScoreComponent(
                    name=name,
                    value=value,
                    weight=weight,
                    contribution=contribution,
                )
            )

            total += contribution

        return ScoreResult(
            scorer_name=self.name,
            score=round(total, 6),
            components=tuple(components),
        )