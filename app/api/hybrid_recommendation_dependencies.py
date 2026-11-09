from __future__ import annotations

from fastapi import Request

from app.services.recommendations.hybrid.orchestration import (
    HybridRecommendationOrchestrator,
)


class HybridRecommendationDependencyError(RuntimeError):
    """Raised when the hybrid orchestrator is not configured."""


def get_hybrid_recommendation_orchestrator(
    request: Request,
) -> HybridRecommendationOrchestrator:
    """
    Resolve the configured hybrid recommendation orchestrator.

    The application composition layer must register the fully
    configured orchestrator on app.state.
    """

    orchestrator = getattr(
        request.app.state,
        "hybrid_recommendation_orchestrator",
        None,
    )

    if orchestrator is None:
        raise HybridRecommendationDependencyError(
            "Hybrid recommendation service is not configured."
        )

    if not isinstance(
        orchestrator,
        HybridRecommendationOrchestrator,
    ):
        raise HybridRecommendationDependencyError(
            "Configured hybrid recommendation service "
            "has an invalid type."
        )

    return orchestrator