from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user

from app.database.session import get_db

from app.models.user import User
from app.models.recommendation import Recommendation
from app.models.recommendation_feedback import (
    RecommendationFeedback,
)

from app.schemas.recommendations import (
    RecommendationRequest,
)

from app.schemas.recommendation_api import (
    RecommendationGenerationAPIResponse,
    RecommendationHistoryAPIResponse,
    RecommendationItemAPIResponse,
    RecommendedResourceAPIResponse,
    RecommendationExplanation,
    RecommendationFeedbackCreate,
    RecommendationFeedbackAPIResponse,
)

from app.services.recommendations.recommendation_service import (
    RecommendationApplicationService,
)


router = APIRouter()

recommendation_service = RecommendationApplicationService()


@router.post(
    "/generate",
    response_model=RecommendationGenerationAPIResponse,
    status_code=status.HTTP_200_OK,
)
def generate_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = recommendation_service.generate(
            db=db,
            user=current_user,
            request=request,
        )

        response_items = []

        for record, resource, explanation in result["recommendations"]:

            record.status = "presented"

            response_items.append(
                RecommendationItemAPIResponse(
                    recommendation_id=record.id,
                    resource=RecommendedResourceAPIResponse(
                        id=resource.id,
                        title=resource.title,
                        description=resource.description,
                        resource_type=resource.resource_type,
                        url=resource.url,
                        provider=resource.provider,
                        subject=resource.subject,
                        language=resource.language,
                        difficulty_level=resource.difficulty_level,
                        estimated_duration_minutes=(
                            resource.estimated_duration_minutes
                        ),
                        quality_score=(
                            float(resource.quality_score)
                            if resource.quality_score is not None
                            else None
                        ),
                    ),
                    explanation=explanation,
                    status=record.status,
                    generated_at=record.generated_at,
                )
            )

        db.commit()

        return RecommendationGenerationAPIResponse(
            request_id=result["request_id"],
            total_results=len(response_items),
            recommendations=response_items,
            generated_at=result["generated_at"],
            algorithm_version=result["algorithm_version"],
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recommendation generation failed.",
        ) from exc


@router.get(
    "/",
    response_model=RecommendationHistoryAPIResponse,
)
def get_recommendations(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100.",
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset cannot be negative.",
        )

    statement = (
        select(Recommendation)
        .where(
            Recommendation.user_id == current_user.id
        )
        .options(
            selectinload(Recommendation.resource)
        )
        .order_by(
            Recommendation.generated_at.desc(),
            Recommendation.rank_position.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    records = list(
        db.scalars(statement).all()
    )

    response_items = []

    for record in records:

        metadata = record.recommendation_metadata or {}

        explanation_data = metadata.get("explanation")

        if not explanation_data:
            continue

        explanation = RecommendationExplanation.model_validate(
            explanation_data
        )

        resource = record.resource

        response_items.append(
            RecommendationItemAPIResponse(
                recommendation_id=record.id,
                resource=RecommendedResourceAPIResponse(
                    id=resource.id,
                    title=resource.title,
                    description=resource.description,
                    resource_type=resource.resource_type,
                    url=resource.url,
                    provider=resource.provider,
                    subject=resource.subject,
                    language=resource.language,
                    difficulty_level=resource.difficulty_level,
                    estimated_duration_minutes=(
                        resource.estimated_duration_minutes
                    ),
                    quality_score=(
                        float(resource.quality_score)
                        if resource.quality_score is not None
                        else None
                    ),
                ),
                explanation=explanation,
                status=record.status,
                generated_at=record.generated_at,
            )
        )

    return RecommendationHistoryAPIResponse(
        total_results=len(response_items),
        recommendations=response_items,
    )


@router.post(
    "/{recommendation_id}/feedback",
    response_model=RecommendationFeedbackAPIResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_recommendation_feedback(
    recommendation_id: UUID,
    request: RecommendationFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recommendation = db.scalar(
        select(Recommendation).where(
            Recommendation.id == recommendation_id,
            Recommendation.user_id == current_user.id,
        )
    )

    if recommendation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found.",
        )

    existing_feedback = db.scalar(
        select(RecommendationFeedback).where(
            RecommendationFeedback.recommendation_id
            == recommendation_id
        )
    )

    if existing_feedback is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback has already been submitted.",
        )

    feedback = RecommendationFeedback(
        recommendation_id=recommendation_id,
        feedback_type=request.feedback_type,
        comment=request.comment,
    )

    db.add(feedback)

    try:
        db.commit()
        db.refresh(feedback)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save recommendation feedback.",
        ) from exc

    return RecommendationFeedbackAPIResponse(
        id=feedback.id,
        recommendation_id=feedback.recommendation_id,
        feedback_type=feedback.feedback_type,
        comment=feedback.comment,
        created_at=feedback.created_at,
    )