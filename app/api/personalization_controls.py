from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db

from app.models.user import User

from app.schemas.personalization_controls import (
    PersonalizationControlsUpdate,
    PersonalizationControlsResponse,
    PersonalizationControlsResetResponse,
)

from app.services.personalization_controls_service import (
    PersonalizationControlsService,
)


router = APIRouter()


@router.get(
    "/",
    response_model=PersonalizationControlsResponse,
    summary="Get student personalization controls",
)
def get_personalization_controls(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve personalization preferences belonging
    exclusively to the authenticated student.
    """

    try:
        preferences = (
            PersonalizationControlsService.get_controls(
                db=db,
                user_id=current_user.id,
            )
        )

        return PersonalizationControlsResponse.model_validate(
            preferences
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve personalization controls.",
        ) from exc


@router.patch(
    "/",
    response_model=PersonalizationControlsResponse,
    summary="Update student personalization controls",
)
def update_personalization_controls(
    request: PersonalizationControlsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update only the personalization preferences
    supplied by the authenticated student.
    """

    if not request.model_fields_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one preference must be provided.",
        )

    try:
        preferences = (
            PersonalizationControlsService.update_controls(
                db=db,
                user_id=current_user.id,
                request=request,
            )
        )

        return PersonalizationControlsResponse.model_validate(
            preferences
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update personalization controls.",
        ) from exc


@router.post(
    "/reset",
    response_model=PersonalizationControlsResetResponse,
    summary="Reset personalization controls",
)
def reset_personalization_controls(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reset configurable preferences to their defaults.

    Learning goals and behavioral history are preserved.
    """

    try:
        preferences = (
            PersonalizationControlsService.reset_controls(
                db=db,
                user_id=current_user.id,
            )
        )

        controls = PersonalizationControlsResponse.model_validate(
            preferences
        )

        return PersonalizationControlsResetResponse(
            message="Personalization controls reset successfully.",
            controls=controls,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to reset personalization controls.",
        ) from exc