from dataclasses import dataclass

from app.services.opportunities.ranking.exceptions import (
    OpportunityRankingConfigurationError,
)


@dataclass(frozen=True)
class RelevanceWeights:
    skills: float = 0.35
    opportunity_type: float = 0.20
    interests: float = 0.20
    location: float = 0.10
    academic_level: float = 0.10
    query: float = 0.05

    def __post_init__(self):

        values = (
            self.skills,
            self.opportunity_type,
            self.interests,
            self.location,
            self.academic_level,
            self.query,
        )

        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < 0
            for value in values
        ):
            raise OpportunityRankingConfigurationError(
                "Relevance weights must be non-negative numbers."
            )

        if abs(sum(values) - 1.0) > 1e-9:
            raise OpportunityRankingConfigurationError(
                "Relevance weights must sum to 1.0."
            )


@dataclass(frozen=True)
class RankingSettings:
    relevance_weight: float = 0.70
    quality_weight: float = 0.30

    minimum_quality_score: float = 0.0

    exclude_unknown_eligibility: bool = False
    exclude_stale_opportunities: bool = False

    def __post_init__(self):

        values = (
            self.relevance_weight,
            self.quality_weight,
        )

        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < 0
            or value > 1
            for value in values
        ):
            raise OpportunityRankingConfigurationError(
                "Ranking weights must be between 0 and 1."
            )

        if abs(sum(values) - 1.0) > 1e-9:
            raise OpportunityRankingConfigurationError(
                "Final ranking weights must sum to 1.0."
            )

        if (
            isinstance(self.minimum_quality_score, bool)
            or not isinstance(self.minimum_quality_score, (int, float))
            or not 0 <= self.minimum_quality_score <= 100
        ):
            raise OpportunityRankingConfigurationError(
                "minimum_quality_score must be between 0 and 100."
            )