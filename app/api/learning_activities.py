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

from app.schemas.behavioral_signals import (
    LearningActivityCreate,
    LearningActivityResponse,
    BehavioralSignalCollection,
)

from app.services.behavioral_signal_service import (
    BehavioralSignalService,
)


router = APIRouter()

behavioral_signal_service = BehavioralSignalService()


# ============================================================
# RECORD LEARNING ACTIVITY
# ============================================================


@router.post(
    "/",
    response_model=LearningActivityResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_learning_activity(
    request: LearningActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:

        activity = behavioral_signal_service.record_activity(
            db=db,
            user_id=current_user.id,
            request=request,
        )

        db.commit()

        db.refresh(activity)

        return activity

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to record learning activity.",
        ) from exc


# ============================================================
# GET BEHAVIORAL SIGNALS
# ============================================================


@router.get(
    "/signals",
    response_model=BehavioralSignalCollection,
)
def get_behavioral_signals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:

        return behavioral_signal_service.build_signals(
            db=db,
            user_id=current_user.id,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate behavioral signals.",
        ) from exc