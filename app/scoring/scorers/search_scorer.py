from app.scoring.base import BaseScorer
from app.scoring.configuration import ScoringConfiguration


class SearchScorer(BaseScorer):

    name = "search"

    def __init__(self, configuration=None):
        super().__init__(
            configuration or ScoringConfiguration(
                weights={
                    "semantic_similarity": 0.40,
                    "keyword_match": 0.25,
                    "content_quality": 0.20,
                    "source_reliability": 0.15,
                }
            )
        )

    def calculate_components(self, data):
        return {
            "semantic_similarity": data["semantic_similarity"],
            "keyword_match": data["keyword_match"],
            "content_quality": data["content_quality"],
            "source_reliability": data["source_reliability"],
        }