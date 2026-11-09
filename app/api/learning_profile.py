from uuid import UUID

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

from app.schemas.learning_profile import (
    LearningGoalCreate,
    LearningGoalResponse,
    LearningGoalUpdate,
    LearningProfileUpdate,
    LearningProfileResponse,
)

from app.services.learning_profile_service import (
    LearningProfileService,
)


router = APIRouter()

learning_profile_service = LearningProfileService()


# ============================================================
# GET LEARNING PROFILE
# ============================================================


@router.get(
    "/",
    response_model=LearningProfileResponse,
)
def get_learning_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:

        result = learning_profile_service.get_profile(
            db=db,
            user=current_user,
        )

        db.commit()

        return result

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve learning profile.",
        ) from exc


# ============================================================
# UPDATE LEARNING PROFILE
# ============================================================


@router.patch(
    "/",
    response_model=LearningProfileResponse,
)
def update_learning_profile(
    request: LearningProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:

        result = learning_profile_service.update_profile(
            db=db,
            user=current_user,
            request=request,
        )

        db.commit()

        return result

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update learning profile.",
        ) from exc


# ============================================================
# LIST LEARNING GOALS
# ============================================================


@router.get(
    "/goals",
    response_model=list[LearningGoalResponse],
)
def list_learning_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:

        result = learning_profile_service.list_goals(
            db=db,
            user=current_user,
        )

        db.commit()

        return result

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve learning goals.",
        ) from exc


# ============================================================
# CREATE LEARNING GOAL
# ============================================================


@router.post(
    "/goals",
    response_model=LearningGoalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_learning_goal(
    request: LearningGoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:

        result = learning_profile_service.create_goal(
            db=db,
            user=current_user,
            request=request,
        )

        db.commit()

        return result

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create learning goal.",
        ) from exc


# ============================================================
# UPDATE LEARNING GOAL
# ============================================================


@router.patch(
    "/goals/{goal_id}",
    response_model=LearningGoalResponse,
)
def update_learning_goal(
    goal_id: UUID,
    request: LearningGoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:

        result = learning_profile_service.update_goal(
            db=db,
            user=current_user,
            goal_id=goal_id,
            request=request,
        )

        if result is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning goal not found.",
            )

        db.commit()

        return result

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update learning goal.",
        ) from exc


# ============================================================
# DELETE LEARNING GOAL
# ============================================================


@router.delete(
    "/goals/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_learning_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:

        deleted = learning_profile_service.delete_goal(
            db=db,
            user=current_user,
            goal_id=goal_id,
        )

        if not deleted:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning goal not found.",
            )

        db.commit()

        return None

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete learning goal.",
        ) from exc