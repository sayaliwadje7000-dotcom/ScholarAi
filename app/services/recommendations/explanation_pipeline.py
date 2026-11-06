from __future__ import annotations

from app.schemas.recommendation_context import (
    RecommendationContext,
)

from app.schemas.recommendation_explanation import (
    RecommendationExplanation,
)

from app.services.recommendations.ranking_service import (
    RankedRecommendation,
)

from app.services.recommendations.explanation_service import (
    RecommendationExplanationService,
)


class RecommendationExplanationPipeline:
    """
    Coordinates explanation generation for ranked recommendations.
    """

    def __init__(
        self,
        explanation_service: (
            RecommendationExplanationService | None
        ) = None,
    ):

        self.explanation_service = (
            explanation_service
            if explanation_service is not None
            else RecommendationExplanationService()
        )

    def execute(
        self,
        ranked_recommendations: list[RankedRecommendation],
        context: RecommendationContext,
    ) -> list[RecommendationExplanation]:

        return self.explanation_service.explain_many(
            ranked_recommendations=ranked_recommendations,
            context=context,
        )