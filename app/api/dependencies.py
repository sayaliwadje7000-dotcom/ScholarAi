"""
ScholarAI API Authentication Dependencies.

Validates JWT access tokens and resolves
the authenticated user from PostgreSQL.
"""

import logging

from uuid import UUID

from fastapi import (
    Depends,
    HTTPException,
    status,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from sqlalchemy import select

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.models.user import User

from app.security.token import decode_access_token

from app.security.token_exceptions import (
    TokenValidationError,
)


logger = logging.getLogger(__name__)


bearer_scheme = HTTPBearer(
    auto_error=False,
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),

    db: Session = Depends(get_db),

) -> User:
    """
    Resolve the currently authenticated user.

    The request must contain:

        Authorization: Bearer <JWT>

    The token is validated before the user is
    retrieved from the database.

    Inactive or deleted users cannot authenticate.
    """

    authentication_error = HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Invalid or expired access token.",

        headers={
            "WWW-Authenticate": "Bearer",
        },

    )

    if credentials is None:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Authentication credentials are required.",

            headers={
                "WWW-Authenticate": "Bearer",
            },

        )

    if credentials.scheme.lower() != "bearer":

        raise authentication_error

    try:

        claims = decode_access_token(
            credentials.credentials
        )

        user_id = UUID(
            claims["sub"]
        )

    except (
        TokenValidationError,
        KeyError,
        ValueError,
        TypeError,
    ):

        raise authentication_error

    try:

        user = db.scalar(

            select(User).where(
                User.id == user_id
            )

        )

    except Exception as exc:

        logger.exception(
            "Database failure while resolving authenticated user."
        )

        raise HTTPException(

            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,

            detail="Authentication service is temporarily unavailable.",

        ) from exc

    if user is None or not user.is_active:

        raise authentication_error

    return user