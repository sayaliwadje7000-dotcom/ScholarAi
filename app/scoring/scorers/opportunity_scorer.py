from app.scoring.base import BaseScorer
from app.scoring.configuration import ScoringConfiguration


class OpportunityScorer(BaseScorer):

    name = "opportunity"

    def __init__(self, configuration=None):
        super().__init__(
            configuration or ScoringConfiguration(
                weights={
                    "skill_match": 0.30,
                    "interest_match": 0.25,
                    "eligibility_match": 0.25,
                    "deadline_feasibility": 0.10,
                    "opportunity_quality": 0.10,
                }
            )
        )

    def calculate_components(self, data):
        return {
            "skill_match": data["skill_match"],
            "interest_match": data["interest_match"],
            "eligibility_match": data["eligibility_match"],
            "deadline_feasibility": data["deadline_feasibility"],
            "opportunity_quality": data["opportunity_quality"],
        }