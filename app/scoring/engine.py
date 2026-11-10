from app.scoring.exceptions import ScorerNotFoundError
from app.scoring.registry import ScorerRegistry


class ScoringEngine:

    def __init__(self, registry: ScorerRegistry):
        self.registry = registry

    def score(
        self,
        scorer_name: str,
        data: dict,
    ):
        scorer = self.registry.get(scorer_name)

        if scorer is None:
            raise ScorerNotFoundError(
                f"Scorer '{scorer_name}' is not registered."
            )

        return scorer.score(data)