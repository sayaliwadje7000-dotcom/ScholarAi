from app.scoring.base import BaseScorer
from app.scoring.configuration import ScoringConfiguration


class PersonalizationScorer(BaseScorer):

    name = "personalization"

    def __init__(self, configuration=None):
        super().__init__(
            configuration or ScoringConfiguration(
                weights={
                    "interest_alignment": 0.30,
                    "learning_goal_alignment": 0.25,
                    "skill_level_match": 0.20,
                    "learning_history_alignment": 0.15,
                    "format_preference": 0.10,
                }
            )
        )

    def calculate_components(self, data):
        return {
            "interest_alignment": data["interest_alignment"],
            "learning_goal_alignment": data["learning_goal_alignment"],
            "skill_level_match": data["skill_level_match"],
            "learning_history_alignment": data[
                "learning_history_alignment"
            ],
            "format_preference": data["format_preference"],
        }