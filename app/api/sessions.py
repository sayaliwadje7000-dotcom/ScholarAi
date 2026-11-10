"""
ScholarAI Phase 18.6 — Session Management API.

Provides authenticated session listing and revocation.
All operations are scoped to the authenticated user.
"""

import uuid

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db

from app.models.user import User
from app.models.user_session import UserSession

from app.schemas.session import (
    SessionListResponse,
    SessionResponse,
    SessionRevocationResponse,
)


router = APIRouter()


@router.get(
    "",
    response_model=SessionListResponse,
)
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List sessions belonging exclusively to the authenticated user.
    """

    sessions = db.scalars(
        select(UserSession)
        .where(UserSession.user_id == current_user.id)
        .order_by(UserSession.created_at.desc())
    ).all()

    return SessionListResponse(
        sessions=[
            SessionResponse.model_validate(session)
            for session in sessions
        ]
    )


@router.delete(
    "/{session_id}",
    response_model=SessionRevocationResponse,
)
def revoke_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke one session owned by the authenticated user.
    """

    session = db.scalar(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
        )
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    if session.revoked_at is not None:
        return SessionRevocationResponse(
            message="Session is already revoked.",
            session_id=session.id,
        )

    session.revoked_at = datetime.now(timezone.utc)
    session.revoke_reason = "user_revoked"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to revoke session.",
        )

    return SessionRevocationResponse(
        message="Session revoked successfully.",
        session_id=session.id,
    )


@router.delete(
    "",
    response_model=SessionRevocationResponse,
)
def revoke_all_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke every active session belonging to the authenticated user.
    """

    now = datetime.now(timezone.utc)

    try:
        db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == current_user.id,
                UserSession.revoked_at.is_(None),
            )
            .values(
                revoked_at=now,
                revoke_reason="user_revoked_all",
            )
        )

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to revoke sessions.",
        )

    return SessionRevocationResponse(
        message="All active sessions have been revoked."
    )