from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScoreComponent:
    name: str
    value: float
    weight: float
    contribution: float


@dataclass(frozen=True)
class ScoreResult:
    scorer_name: str
    score: float
    components: tuple[ScoreComponent, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Score must be between 0 and 1.")

        if not self.scorer_name:
            raise ValueError("Scorer name cannot be empty.")

        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary.")

    @property
    def percentage(self) -> float:
        return round(self.score * 100, 2)