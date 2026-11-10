from app.scoring.base import BaseScorer
from app.scoring.configuration import ScoringConfiguration


class RAGScorer(BaseScorer):

    name = "rag"

    def __init__(self, configuration=None):
        super().__init__(
            configuration or ScoringConfiguration(
                weights={
                    "semantic_relevance": 0.40,
                    "keyword_relevance": 0.20,
                    "document_quality": 0.20,
                    "source_reliability": 0.20,
                }
            )
        )

    def calculate_components(self, data):
        return {
            "semantic_relevance": data["semantic_relevance"],
            "keyword_relevance": data["keyword_relevance"],
            "document_quality": data["document_quality"],
            "source_reliability": data["source_reliability"],
        }