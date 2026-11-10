from app.scoring.base import BaseScorer
from app.scoring.configuration import ScoringConfiguration


class AnswerScorer(BaseScorer):

    name = "answer"

    def __init__(self, configuration=None):
        super().__init__(
            configuration or ScoringConfiguration(
                weights={
                    "correctness": 0.35,
                    "relevance": 0.25,
                    "completeness": 0.20,
                    "clarity": 0.10,
                    "citation_support": 0.10,
                }
            )
        )

    def calculate_components(self, data):
        return {
            "correctness": data["correctness"],
            "relevance": data["relevance"],
            "completeness": data["completeness"],
            "clarity": data["clarity"],
            "citation_support": data["citation_support"],
        }