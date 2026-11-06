from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas.recommendation_context import (
    RecommendationContext,
)

from app.schemas.recommendation_explanation import (
    ExplanationFactor,
    RecommendationExplanation,
)

from app.services.recommendations.ranking_service import (
    RankedRecommendation,
)


class RecommendationExplanationService:
    """
    Generates deterministic, evidence-based recommendation explanations.

    Explanations are derived exclusively from:
    - Recommendation scoring results
    - Resource classification
    - User learning context
    - Explicit recommendation intent

    No external LLM calls are performed.
    """

    EXPLANATION_VERSION = "v1"

    FACTOR_DEFINITIONS = (
        (
            "topic_relevance",
            "Topic Relevance",
        ),
        (
            "learning_level",
            "Learning Level",
        ),
        (
            "prerequisite_compatibility",
            "Prerequisite Compatibility",
        ),
        (
            "resource_quality",
            "Resource Quality",
        ),
        (
            "learning_objective",
            "Learning Objective Relevance",
        ),
        (
            "freshness",
            "Content Freshness",
        ),
    )

    @staticmethod
    def _normalize(value: Any) -> str:
        if value is None:
            return ""

        return str(
            getattr(value, "value", value)
        ).strip().casefold()

    @staticmethod
    def _number(value: Any) -> float:
        return float(value)

    def _describe_factor(
        self,
        factor_name: str,
        score: float,
        resource: Any,
        context: RecommendationContext,
    ) -> tuple[str, bool]:
        """
        Generate an evidence-based description.

        Returns:
            description
            whether the factor should be considered a highlight
        """

        learning_context = context.learning_context
        intent = context.intent

        if factor_name == "topic_relevance":

            has_topic_context = bool(
                intent.query
                or intent.subject
                or learning_context.preferred_subjects
            )

            if not has_topic_context:
                return (
                    "Topic relevance was treated as neutral because "
                    "no topic preference or search query was supplied.",
                    False,
                )

            if score >= 0.75:
                return (
                    "The resource has a strong match with the requested "
                    "topic or preferred academic subjects.",
                    True,
                )

            if score >= 0.50:
                return (
                    "The resource has a partial match with the requested "
                    "topic or preferred academic subjects.",
                    True,
                )

            return (
                "The resource has limited topic overlap with the "
                "available learning context.",
                False,
            )

        if factor_name == "learning_level":

            requested_level = intent.difficulty_level

            if not requested_level:
                return (
                    "Learning-level compatibility was treated as neutral "
                    "because no difficulty preference was supplied.",
                    False,
                )

            if score >= 0.99:
                return (
                    "The resource difficulty matches the requested "
                    "learning level.",
                    True,
                )

            if score >= 0.49:
                return (
                    "The resource difficulty is close to the requested "
                    "learning level.",
                    True,
                )

            return (
                "The resource difficulty differs from the requested "
                "learning level.",
                False,
            )

        if factor_name == "prerequisite_compatibility":

            prerequisites = resource.prerequisites or []

            if not prerequisites:
                return (
                    "No prerequisite topics are listed for this resource.",
                    True,
                )

            return (
                "The resource has listed prerequisites. Their mastery "
                "has not been independently verified.",
                False,
            )

        if factor_name == "resource_quality":

            quality = resource.quality_score

            if quality is None:
                return (
                    "No resource quality rating is available; "
                    "a neutral quality value was used.",
                    False,
                )

            quality = float(quality)

            return (
                f"The resource has a quality rating of "
                f"{quality:.1f} out of 5.",
                quality >= 3.5,
            )

        if factor_name == "learning_objective":

            objectives = resource.learning_objectives or []

            goals = learning_context.learning_goals or []

            if not objectives or not goals:
                return (
                    "Learning-objective relevance was treated as neutral "
                    "because sufficient learning-goal information "
                    "was unavailable.",
                    False,
                )

            if score >= 0.75:
                return (
                    "The resource learning objectives strongly align "
                    "with the student's stated learning goals.",
                    True,
                )

            if score >= 0.50:
                return (
                    "The resource learning objectives partially align "
                    "with the student's stated learning goals.",
                    True,
                )

            return (
                "The resource has limited overlap with the stated "
                "learning goals.",
                False,
            )

        if factor_name == "freshness":

            published_at = resource.published_at

            if published_at is None:
                return (
                    "No publication date is available; a neutral "
                    "freshness value was used.",
                    False,
                )

            return (
                "The resource publication date was considered "
                "when calculating its freshness score.",
                score >= 0.50,
            )

        return (
            "This factor contributed to the recommendation score.",
            False,
        )

    def _build_factors(
        self,
        ranked: RankedRecommendation,
        context: RecommendationContext,
    ) -> list[ExplanationFactor]:

        breakdown = ranked.scoring_result.breakdown

        weights = ranked.scoring_result.weights

        factors = []

        for factor_name, display_name in self.FACTOR_DEFINITIONS:

            factor_score = self._number(
                getattr(breakdown, factor_name)
            )

            factor_weight = self._number(
                getattr(weights, factor_name)
            )

            weighted_contribution = (
                factor_score * factor_weight
            )

            description, _ = self._describe_factor(
                factor_name=factor_name,
                score=factor_score,
                resource=ranked.resource,
                context=context,
            )

            factors.append(
                ExplanationFactor(
                    factor=display_name,
                    score=round(factor_score, 4),
                    weight=round(factor_weight, 4),
                    weighted_contribution=round(
                        weighted_contribution,
                        4,
                    ),
                    description=description,
                )
            )

        return factors

    def _build_highlights(
        self,
        ranked: RankedRecommendation,
        context: RecommendationContext,
        factors: list[ExplanationFactor],
    ) -> list[str]:

        eligible = []

        for factor in factors:

            factor_name = next(
                (
                    name
                    for name, display_name in self.FACTOR_DEFINITIONS
                    if display_name == factor.factor
                ),
                None,
            )

            if factor_name is None:
                continue

            _, is_highlight = self._describe_factor(
                factor_name=factor_name,
                score=factor.score,
                resource=ranked.resource,
                context=context,
            )

            if not is_highlight:
                continue

            eligible.append(factor)

        eligible.sort(
            key=lambda factor: (
                -factor.weighted_contribution,
                factor.factor,
            )
        )

        return [
            factor.description
            for factor in eligible[:3]
        ]

    def explain(
        self,
        ranked: RankedRecommendation,
        context: RecommendationContext,
    ) -> RecommendationExplanation:
        """
        Generate an explanation for one ranked recommendation.
        """

        if not isinstance(
            ranked,
            RankedRecommendation,
        ):
            raise TypeError(
                "Expected RankedRecommendation."
            )

        if not isinstance(
            context,
            RecommendationContext,
        ):
            raise TypeError(
                "Expected RecommendationContext."
            )

        factors = self._build_factors(
            ranked,
            context,
        )

        highlights = self._build_highlights(
            ranked,
            context,
            factors,
        )

        if highlights:

            reason = (
                "Recommended because "
                + " ".join(highlights[:2])
            )

        else:

            reason = (
                "Recommended based on the combined scoring factors "
                "and the requested recommendation filters."
            )

        return RecommendationExplanation(
            resource_id=ranked.resource_id,
            rank_position=ranked.rank_position,
            recommendation_score=round(
                self._number(ranked.score),
                4,
            ),
            reason=reason[:500],
            highlights=highlights,
            factors=factors,
            algorithm_version=ranked.algorithm_version,
            explanation_version=self.EXPLANATION_VERSION,
        )

    def explain_many(
        self,
        ranked_recommendations: list[RankedRecommendation],
        context: RecommendationContext,
    ) -> list[RecommendationExplanation]:
        """
        Generate explanations for an entire ranked recommendation list.

        Original ranking order is preserved.
        """

        if not isinstance(
            context,
            RecommendationContext,
        ):
            raise TypeError(
                "Expected RecommendationContext."
            )

        return [
            self.explain(
                ranked=ranked,
                context=context,
            )
            for ranked in ranked_recommendations
        ]