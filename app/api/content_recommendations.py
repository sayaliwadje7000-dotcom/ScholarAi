from __future__ import annotations

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.schemas.content_recommendations import (
    ContentRecommendationRequest,
    ContentRecommendationResponse,
)

from app.services.recommendations.content_based.recommendation_service import (
    ContentBasedRecommendationService,
    ContentRecommendationServiceError,
)

from app.api.dependencies import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["Content-Based Recommendations"],
)


def get_content_recommendation_service():

    raise NotImplementedError(
        "Configure the content recommendation service "
        "dependency before enabling this endpoint."
    )


@router.post(
    "/content-based",
    response_model=ContentRecommendationResponse,
    status_code=status.HTTP_200_OK,
)
def generate_content_recommendations(
    request: ContentRecommendationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    service: ContentBasedRecommendationService = Depends(
        get_content_recommendation_service
    ),
):

    try:

        return service.recommend(
            db=db,
            user_id=current_user.id,
            request=request,
        )

    except ContentRecommendationServiceError as exc:

        logger.exception(
            "Content recommendation generation failed."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate recommendations.",
        ) from exc