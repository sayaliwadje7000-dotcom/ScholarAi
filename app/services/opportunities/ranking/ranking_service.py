from dataclasses import dataclass
from typing import Any

from app.services.opportunities.validity import (
    OpportunityValidityService,
)

from app.services.opportunities.ranking.configuration import (
    RankingSettings,
)

from app.services.opportunities.ranking.quality_assessor import (
    OpportunityQualityAssessor,
    QualityEvaluation,
)

from app.services.opportunities.ranking.relevance_scorer import (
    OpportunityRelevanceScorer,
    RelevanceEvaluation,
)


@dataclass(frozen=True)
class RankedOpportunity:
    opportunity: dict[str, Any]

    quality: QualityEvaluation
    relevance: RelevanceEvaluation

    validity: Any

    final_score: float
    rank: int

    explanations: tuple[str, ...]


@dataclass(frozen=True)
class OpportunityRankingResponse:
    ranked_opportunities: tuple[RankedOpportunity, ...]

    total_received: int
    total_ranked: int
    total_excluded: int

    exclusion_reasons: dict[str, int]


class OpportunityRankingService:
    """
    Coordinates validity, quality, relevance and final ranking.
    """

    def __init__(
        self,
        validity_service: OpportunityValidityService | None = None,
        quality_assessor: OpportunityQualityAssessor | None = None,
        relevance_scorer: OpportunityRelevanceScorer | None = None,
        settings: RankingSettings | None = None,
    ):

        self.validity_service = (
            validity_service
            or OpportunityValidityService()
        )

        self.quality_assessor = (
            quality_assessor
            or OpportunityQualityAssessor()
        )

        self.relevance_scorer = (
            relevance_scorer
            or OpportunityRelevanceScorer()
        )

        self.settings = settings or RankingSettings()

    def rank(
        self,
        opportunities: list[dict[str, Any]],
        student_profile: dict[str, Any] | None = None,
        query: str | None = None,
        limit: int | None = None,
        now=None,
    ) -> OpportunityRankingResponse:

        if not isinstance(opportunities, list):
            raise ValueError(
                "opportunities must be a list."
            )

        if student_profile is None:
            student_profile = {}

        if not isinstance(student_profile, dict):
            raise ValueError(
                "student_profile must be a dictionary."
            )

        if limit is not None and (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit <= 0
        ):
            raise ValueError(
                "limit must be a positive integer."
            )

        ranked = []
        exclusions = {}

        def exclude(reason):
            exclusions[reason] = exclusions.get(reason, 0) + 1

        for opportunity in opportunities:

            if not isinstance(opportunity, dict):
                raise ValueError(
                    "Every opportunity must be a dictionary."
                )

            validity = self.validity_service.evaluate(
                opportunity=opportunity,
                student_profile=student_profile,
                now=now,
            )

            # Hard validity constraints.
            if not opportunity.get("is_active", True):
                exclude("inactive")
                continue

            if validity.deadline.status in {
                "expired",
                "cancelled",
                "closed",
            }:
                exclude(validity.deadline.status)
                continue

            if validity.eligibility.status == "not_eligible":
                exclude("not_eligible")
                continue

            if (
                self.settings.exclude_unknown_eligibility
                and validity.eligibility.status == "unknown"
            ):
                exclude("unknown_eligibility")
                continue

            if (
                self.settings.exclude_stale_opportunities
                and validity.freshness.requires_refresh
            ):
                exclude("stale")
                continue

            quality = self.quality_assessor.evaluate(
                opportunity
            )

            if quality.score < self.settings.minimum_quality_score:
                exclude("below_minimum_quality")
                continue

            relevance = self.relevance_scorer.evaluate(
                opportunity=opportunity,
                student_profile=student_profile,
                query=query,
            )

            final_score = (
                relevance.score * self.settings.relevance_weight
                + quality.score * self.settings.quality_weight
            )

            explanations = []

            explanations.extend(quality.reasons)
            explanations.extend(relevance.reasons)

            if validity.eligibility.status == "unknown":
                explanations.append(
                    "Eligibility is not fully determined because profile information is missing."
                )

            if validity.freshness.requires_refresh:
                explanations.append(
                    "Opportunity information requires a refresh."
                )

            ranked.append(
                {
                    "opportunity": opportunity,
                    "quality": quality,
                    "relevance": relevance,
                    "validity": validity,
                    "final_score": round(final_score, 2),
                    "explanations": tuple(explanations),
                }
            )

        # Deterministic tie-breaking:
        # 1. Higher composite score.
        # 2. Higher relevance score.
        # 3. Higher quality score.
        # 4. Stable title ordering.
        ranked.sort(
            key=lambda item: (
                -item["final_score"],
                -item["relevance"].score,
                -item["quality"].score,
                str(item["opportunity"].get("title", "")).casefold(),
            )
        )

        if limit is not None:
            ranked = ranked[:limit]

        results = tuple(
            RankedOpportunity(
                opportunity=item["opportunity"],
                quality=item["quality"],
                relevance=item["relevance"],
                validity=item["validity"],
                final_score=item["final_score"],
                rank=index,
                explanations=item["explanations"],
            )
            for index, item in enumerate(ranked, start=1)
        )

        return OpportunityRankingResponse(
            ranked_opportunities=results,
            total_received=len(opportunities),
            total_ranked=len(results),
            total_excluded=sum(exclusions.values()),
            exclusion_reasons=exclusions,
        )