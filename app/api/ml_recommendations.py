from __future__ import annotations

import logging

from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.api.dependencies import get_current_user

from app.api.ml_recommendation_dependencies import (
    get_ml_recommendation_service,
)

from app.models.user import User

from app.schemas.ml_recommendations import (
    MLRecommendationItem,
    MLRecommendationRequest,
    MLRecommendationResponse,
)

from app.services.recommendations.ml.inference.recommendation_service import (
    RecommendationMLService,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["ML Recommendations"],
)


@router.post(
    "/ml",
    response_model=MLRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate ML-based recommendations",
)
def generate_ml_recommendations(
    request: MLRecommendationRequest,
    current_user: User = Depends(get_current_user),
    service: RecommendationMLService = Depends(
        get_ml_recommendation_service
    ),
):
    prediction_at = (
        request.prediction_at
        or datetime.now(timezone.utc)
    )

    if (
        prediction_at.tzinfo is None
        or prediction_at.utcoffset() is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="prediction_at must include a timezone.",
        )

    if len(set(request.resource_ids)) != len(
        request.resource_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="resource_ids must not contain duplicates.",
        )

    try:
        result = service.predict(
            user_id=current_user.id,
            resource_ids=request.resource_ids,
            prediction_at=prediction_at,
        )

    except Exception as exc:
        logger.exception(
            "ML recommendation inference failed."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML recommendations are temporarily unavailable.",
        ) from exc

    try:
        recommendations = [
            MLRecommendationItem(
                resource_id=item.resource_id,
                relevance_probability=(
                    item.relevance_probability
                ),
                is_relevant=item.is_relevant,
            )
            for item in result.predictions
        ]

        return MLRecommendationResponse(
            user_id=current_user.id,
            model_run_id=result.model_run_id,
            total_results=len(recommendations),
            recommendations=recommendations,
            generated_at=datetime.now(timezone.utc),
        )

    except Exception as exc:
        logger.exception(
            "Unable to serialize ML recommendation result."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to format ML recommendations.",
        ) from exc