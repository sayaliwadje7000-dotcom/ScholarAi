from app.scoring.engine import ScoringEngine
from app.scoring.registry import ScorerRegistry
from app.scoring.scorers import (
    ResourceScorer,
    SearchScorer,
    RAGScorer,
    OpportunityScorer,
    AnswerScorer,
    PersonalizationScorer,
)


def create_scoring_engine() -> ScoringEngine:
    registry = ScorerRegistry()

    scorers = [
        ResourceScorer(),
        SearchScorer(),
        RAGScorer(),
        OpportunityScorer(),
        AnswerScorer(),
        PersonalizationScorer(),
    ]

    for scorer in scorers:
        registry.register(scorer)

    return ScoringEngine(registry)