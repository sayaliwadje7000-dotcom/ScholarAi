from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from app.schemas.educational_resource_discovery import (
    ResourceDiscoveryRequest,
)
from app.schemas.educational_resources import (
    EducationalResourceListResponse,
)
from app.services.educational_resources.recommendation_service import (
    ResourceRecommendationService,
)


router = APIRouter(
    prefix="/resources",
    tags=["Educational Resource Recommendations"],
)


def get_resource_recommendation_service(
    request: Request,
) -> ResourceRecommendationService:
    """
    Retrieve the configured recommendation service
    from the FastAPI application state.
    """

    service = getattr(
        request.app.state,
        "resource_recommendation_service",
        None,
    )

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Educational resource recommendation "
                "service is not configured."
            ),
        )

    return service


@router.post(
    "/recommendations",
    response_model=EducationalResourceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Recommend educational resources",
    description=(
        "Searches configured educational resource providers, "
        "filters and deduplicates results, assesses resource "
        "quality, and ranks resources by query relevance."
    ),
)
async def recommend_educational_resources(
    discovery_request: ResourceDiscoveryRequest,
    service: ResourceRecommendationService = Depends(
        get_resource_recommendation_service
    ),
) -> EducationalResourceListResponse:
    """
    Return ranked educational resources for a search query.
    """

    try:
        return await service.recommend(
            discovery_request
        )

    except HTTPException:
        raise

    except Exception as exc:
        # Avoid returning internal provider errors,
        # credentials, or implementation details to clients.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Educational resource recommendation "
                "could not be completed."
            ),
        ) from exc