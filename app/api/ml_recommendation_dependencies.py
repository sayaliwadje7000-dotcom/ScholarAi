from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.services.recommendations.ml.inference.recommendation_service import (
    RecommendationMLService,
)


def get_ml_recommendation_service(
    request: Request,
) -> RecommendationMLService:

    service = getattr(
        request.app.state,
        "ml_recommendation_service",
        None,
    )

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "ML recommendation service is not configured."
            ),
        )

    return service