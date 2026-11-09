from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.schemas.adaptive_recommendations import (
    AdaptationMode,
    AdaptiveRecommendationResult,
)
from app.services.recommendations.adaptive_policy_engine import (
    AdaptivePolicyEngine,
)


class AdaptiveHybridService:
    """
    Integration layer between:

        Phase 16.5 PersonalizedContextEngine
                    |
                    v
        Phase 16.6 AdaptivePolicyEngine
                    |
                    v
        Phase 15 HybridRecommendationOrchestrator

    The Phase 15 orchestrator remains responsible for candidate
    discovery, aggregation, normalization, filtering and ranking.

    The executor callback is the composition boundary to the
    existing Phase 15 execute(context, limit=None) method.
    """

    def __init__(
        self,
        personalized_context_engine,
        hybrid_executor: Callable[..., Any],
        policy_engine: AdaptivePolicyEngine | None = None,
    ) -> None:
        if personalized_context_engine is None:
            raise ValueError(
                "personalized_context_engine is required"
            )

        if not callable(hybrid_executor):
            raise TypeError(
                "hybrid_executor must be callable"
            )

        self.personalized_context_engine = (
            personalized_context_engine
        )
        self.hybrid_executor = hybrid_executor
        self.policy_engine = (
            policy_engine or AdaptivePolicyEngine()
        )

    def generate(
        self,
        *,
        user,
        hybrid_context,
        request=None,
        interactions=None,
        behavioral_signals=None,
        feedback_collection=None,
        limit: int | None = None,
    ) -> AdaptiveRecommendationResult:
        """
        Build personalized context and execute the existing hybrid
        recommendation workflow.

        hybrid_context must be the valid Phase 15 HybridRequestContext
        constructed by the application's composition layer.
        """

        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int):
                raise TypeError("limit must be an integer")

            if limit < 1:
                raise ValueError("limit must be greater than zero")

        user_id = getattr(user, "id", None)

        if not isinstance(user_id, UUID):
            raise ValueError("user.id must be a UUID")

        personalized_context = (
            self.personalized_context_engine.build(
                user=user,
                request=request,
                interactions=interactions,
                behavioral_signals=behavioral_signals,
                feedback_collection=feedback_collection,
            )
        )

        if personalized_context.user_id != user_id:
            raise ValueError(
                "Personalized context user does not match request user"
            )

        policy = self.policy_engine.build_policy(
            personalized_context
        )

        # Phase 15 continues to own hybrid recommendation generation.
        # No candidate scores or component weights are modified here.
        recommendations = self.hybrid_executor(
            hybrid_context,
            limit=limit,
        )

        warnings: list[str] = []

        if policy.mode == AdaptationMode.COLD_START:
            warnings.append(
                "Sparse personalization evidence: "
                "hybrid recommendations use the existing "
                "non-personalized ranking behavior."
            )

        return AdaptiveRecommendationResult(
            user_id=user_id,
            recommendations=recommendations,
            personalization_context=personalized_context,
            policy=policy,
            adaptation_applied=False,
            warnings=tuple(warnings),
        )