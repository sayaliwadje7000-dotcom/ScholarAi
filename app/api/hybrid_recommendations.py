from __future__ import annotations

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.api.dependencies import get_current_user
from app.models.user import User

from app.api.hybrid_recommendation_dependencies import (
    HybridRecommendationDependencyError,
    get_hybrid_recommendation_orchestrator,
)

from app.schemas.hybrid_recommendations import (
    HybridComponentScoreResponse,
    HybridComponentStatusResponse,
    HybridRecommendationExplanationResponse,
    HybridRecommendationItemResponse,
    HybridRecommendationRequest,
    HybridRecommendationResponse,
)

from app.services.recommendations.hybrid.orchestration import (
    HybridOrchestrationError,
    HybridRecommendationOrchestrator,
    HybridRequestContext,
)

from app.services.recommendations.hybrid.explanation import (
    HybridExplanationService,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/recommendations/hybrid",
    tags=["Hybrid Recommendations"],
)


def _build_recommendation_items(result):
    """
    Convert ranked orchestration results into API response items.
    """

    items = []

    explanation_service = HybridExplanationService()

    for ranked in result.ranked_candidates:
        candidate = ranked.resource

        explanation = explanation_service.explain(ranked)

        component_explanations = [
            HybridComponentScoreResponse(
                component=item.component,
                normalized_score=item.normalized_score,
                configured_weight=item.configured_weight,
                effective_weight=item.effective_weight,
                weighted_contribution=item.weighted_contribution,
                explanation=item.explanation,
            )
            for item in explanation.component_explanations
        ]

        explanation_response = (
            HybridRecommendationExplanationResponse(
                resource_id=explanation.resource_id,
                hybrid_score=explanation.hybrid_score,
                rank=explanation.rank,
                component_explanations=component_explanations,
                summary=explanation.summary,
            )
        )

        items.append(
            HybridRecommendationItemResponse(
                resource_id=candidate.resource_id,
                title=candidate.title,
                resource_type=candidate.resource_type,
                description=candidate.description,
                canonical_url=candidate.canonical_url,
                hybrid_score=ranked.score.hybrid_score,
                rank=ranked.rank,
                explanation=explanation_response,
            )
        )

    return items


def _build_component_reports(result):
    return [
        HybridComponentStatusResponse(
            component=report.component.name,
            status=report.status.value,
            candidate_count=report.candidate_count,
            duration_ms=report.duration_ms,
            error_type=report.error_type,
            error_message=report.error_message,
        )
        for report in result.component_reports
    ]


@router.post(
    "",
    response_model=HybridRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate hybrid recommendations",
    description=(
        "Generate recommendations by combining rule-based, "
        "content-based and machine-learning recommendation "
        "components through the hybrid orchestration pipeline."
    ),
)
def generate_hybrid_recommendations(
    payload: HybridRecommendationRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: HybridRecommendationOrchestrator = Depends(
        get_hybrid_recommendation_orchestrator
    ),
):
    """
    Generate hybrid recommendations for an academic query.
    """

    request_id = None

    try:
        context = HybridRequestContext(
            user_id=current_user.id,
            query=payload.query,
            filters=payload.filters,
            metadata=payload.metadata,
        )

        result = orchestrator.execute(
            context,
            limit=payload.limit,
        )

        request_id = result.request_id

        # The orchestration result must retain the authenticated
        # identity supplied in HybridRequestContext. Never trust a
        # user identifier returned by an orchestration component.
        if result.user_id != current_user.id:
            logger.error(
                "Hybrid orchestrator returned a mismatched user ID."
            )
            raise RuntimeError(
                "Hybrid recommendation ownership context mismatch."
            )

        recommendation_items = _build_recommendation_items(
            result
        )

        component_reports = _build_component_reports(
            result
        )

        return HybridRecommendationResponse(
            request_id=result.request_id,
            user_id=current_user.id,
            generated_at=result.generated_at,
            recommendations=recommendation_items,
            component_reports=component_reports,
            total_candidates_discovered=(
                result.total_candidates_discovered
            ),
            total_candidates_after_deduplication=(
                result.total_candidates_after_deduplication
            ),
            total_candidates_scored=(
                result.total_candidates_scored
            ),
            total_candidates_accepted=(
                result.total_candidates_accepted
            ),
            total_candidates_returned=(
                result.total_candidates_returned
            ),
            duration_ms=result.duration_ms,
            fallback_used=result.fallback_used,
            warnings=list(result.warnings),
        )

    except HTTPException:
        raise

    except HybridOrchestrationError:
        logger.exception(
            "Hybrid recommendation orchestration failed."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "hybrid_recommendation_unavailable",
                "message": (
                    "The hybrid recommendation service "
                    "could not complete the request."
                ),
                "request_id": (
                    str(request_id) if request_id else None
                ),
            },
        )

    except Exception:
        logger.exception(
            "Unexpected hybrid recommendation API failure."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_recommendation_error",
                "message": (
                    "An unexpected error occurred while "
                    "generating recommendations."
                ),
                "request_id": (
                    str(request_id) if request_id else None
                ),
            },
        )