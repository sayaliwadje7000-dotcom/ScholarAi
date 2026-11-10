from app.scoring.base import BaseScorer
from app.scoring.configuration import ScoringConfiguration


class ResourceScorer(BaseScorer):

    name = "resource"

    def __init__(self, configuration=None):
        super().__init__(
            configuration or ScoringConfiguration(
                weights={
                    "query_relevance": 0.35,
                    "subject_match": 0.25,
                    "quality": 0.20,
                    "freshness": 0.10,
                    "difficulty_match": 0.10,
                }
            )
        )

    def calculate_components(self, data):
        return {
            "query_relevance": data["query_relevance"],
            "subject_match": data["subject_match"],
            "quality": data["quality"],
            "freshness": data["freshness"],
            "difficulty_match": data["difficulty_match"],
        }