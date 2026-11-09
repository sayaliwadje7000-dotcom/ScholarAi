from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from uuid import UUID

from app.services.recommendations.hybrid.ranking import (
    RankedHybridCandidate,
)


class HybridExplanationError(ValueError):
    """Base exception for hybrid explanation errors."""


@dataclass(frozen=True, slots=True)
class ComponentExplanation:
    component: str

    normalized_score: float

    configured_weight: float

    effective_weight: float

    weighted_contribution: float

    explanation: str


@dataclass(frozen=True, slots=True)
class HybridRecommendationExplanation:
    resource_id: UUID

    hybrid_score: float

    rank: int

    component_explanations: tuple[
        ComponentExplanation,
        ...
    ]

    summary: str

    def __post_init__(self) -> None:

        if not 0.0 <= self.hybrid_score <= 1.0:
            raise HybridExplanationError(
                "hybrid_score must be between zero and one."
            )

        if self.rank < 1:
            raise HybridExplanationError(
                "rank must be positive."
            )

        total_contribution = sum(
            item.weighted_contribution
            for item in self.component_explanations
        )

        if not isclose(
            total_contribution,
            self.hybrid_score,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise HybridExplanationError(
                "Component contributions do not match "
                "the final hybrid score."
            )


class HybridExplanationService:
    """
    Generates transparent explanations from actual score results.

    No language model is used to invent explanations.
    """

    def explain(
        self,
        ranked: RankedHybridCandidate,
    ) -> HybridRecommendationExplanation:

        if not isinstance(
            ranked,
            RankedHybridCandidate,
        ):
            raise HybridExplanationError(
                "ranked must be a RankedHybridCandidate."
            )

        if ranked.resource.resource_id != ranked.score.resource_id:
            raise HybridExplanationError(
                "Candidate and score resource IDs do not match."
            )

        explanations = []

        for contribution in ranked.score.contributions:

            values = (
                contribution.normalized_score,
                contribution.configured_weight,
                contribution.effective_weight,
                contribution.weighted_contribution,
            )

            if any(
                not isfinite(float(value))
                for value in values
            ):
                raise HybridExplanationError(
                    "Contribution contains a non-finite value."
                )

            component_name = contribution.component.name

            explanation = (
                f"{component_name.replace('_', ' ').title()} "
                f"produced a normalized score of "
                f"{contribution.normalized_score:.4f}, "
                f"with an effective weight of "
                f"{contribution.effective_weight:.2%}, "
                f"contributing "
                f"{contribution.weighted_contribution:.4f} "
                f"to the final hybrid score."
            )

            explanations.append(
                ComponentExplanation(
                    component=component_name,
                    normalized_score=contribution.normalized_score,
                    configured_weight=contribution.configured_weight,
                    effective_weight=contribution.effective_weight,
                    weighted_contribution=(
                        contribution.weighted_contribution
                    ),
                    explanation=explanation,
                )
            )

        if not explanations:
            raise HybridExplanationError(
                "A ranked recommendation must have "
                "at least one component contribution."
            )

        summary = (
            f"{ranked.resource.title} received a hybrid score "
            f"of {ranked.score.hybrid_score:.4f} "
            f"and was assigned rank {ranked.rank}."
        )

        return HybridRecommendationExplanation(
            resource_id=ranked.resource.resource_id,
            hybrid_score=ranked.score.hybrid_score,
            rank=ranked.rank,
            component_explanations=tuple(explanations),
            summary=summary,
        )

    def explain_many(
        self,
        ranked_candidates: tuple[
            RankedHybridCandidate,
            ...
        ],
    ) -> tuple[HybridRecommendationExplanation, ...]:

        if not isinstance(ranked_candidates, tuple):
            raise HybridExplanationError(
                "ranked_candidates must be a tuple."
            )

        return tuple(
            self.explain(candidate)
            for candidate in ranked_candidates
        )