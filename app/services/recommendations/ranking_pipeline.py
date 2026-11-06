from __future__ import annotations

from collections.abc import Iterable

from app.schemas.recommendations import (
    RecommendationRequest,
    RecommendationScoringResult,
)

from app.schemas.resource_metadata import (
    ResourceClassification,
)

from app.services.recommendations.filtering_service import (
    RecommendationFilteringService,
)

from app.services.recommendations.ranking_service import (
    RankedRecommendation,
    RecommendationRankingService,
)


class RecommendationRankingPipeline:
    """
    Coordinates filtering and ranking of scored candidates.

    This is an internal Phase 10.7 component.
    """

    def __init__(
        self,
        filtering_service: RecommendationFilteringService | None = None,
        ranking_service: RecommendationRankingService | None = None,
    ):
        self.filtering_service = (
            filtering_service
            if filtering_service is not None
            else RecommendationFilteringService()
        )

        self.ranking_service = (
            ranking_service
            if ranking_service is not None
            else RecommendationRankingService()
        )

    def execute(
        self,
        candidates: Iterable[
            tuple[
                ResourceClassification,
                RecommendationScoringResult,
            ]
        ],
        request: RecommendationRequest,
        interactions: Iterable[object] = (),
    ) -> list[RankedRecommendation]:
        """
        Filter first, then rank.

        No score recalculation or database operations occur here.
        """

        filtered = self.filtering_service.filter(
            candidates=candidates,
            request=request,
            interactions=interactions,
        )

        return self.ranking_service.rank(
            candidates=filtered,
            limit=request.limit,
        )