"""
ScholarAI Authentication API.

Phase 18.2: Registration.
Phase 18.4: Login and credential verification.
Phase 18.5: JWT access-token issuance.
Phase 18.6: Refresh-token and session management.
"""

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.schemas.auth import (
    UserRegistrationRequest,
    UserRegistrationResponse,
    UserLoginRequest,
    UserLoginResponse,
)

from app.schemas.session import RefreshTokenRequest

from app.services.auth_service import auth_service

from app.services.auth_exceptions import AuthenticationError

from app.services.session_service import (
    session_service,
    SessionError,
)

from app.security.token_exceptions import TokenCreationError


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    request: UserRegistrationRequest,
    db: Session = Depends(get_db),
):
    try:
        user = auth_service.register_user(
            db=db,
            request=request,
        )

        return UserRegistrationResponse.model_validate(user)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Registration failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register the account.",
        ) from exc


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
)
def login_user(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
):
    try:
        user = auth_service.authenticate_user(
            db=db,
            request=request,
        )

        tokens = session_service.create_session(
            db=db,
            user=user,
        )

        return UserLoginResponse(
            authenticated=True,
            message="Login successful.",
            user=UserRegistrationResponse.model_validate(user),
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=tokens["expires_in"],
        )

    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    except TokenCreationError as exc:
        logger.exception("Token creation failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete login.",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected login failure.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete login.",
        ) from exc


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
)
def refresh_access_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    try:
        return session_service.rotate_refresh_token(
            db=db,
            refresh_token=request.refresh_token,
        )

    except SessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    except Exception as exc:
        logger.exception("Refresh-token operation failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to refresh authentication.",
        ) from exc