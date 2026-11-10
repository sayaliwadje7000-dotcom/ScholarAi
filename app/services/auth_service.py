"""
ScholarAI Authentication Service.

Responsibilities:
- User registration.
- Email-based account lookup.
- Credential verification.
- Inactive account rejection.
- Password hash upgrades.
"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User

from app.schemas.auth import (
    UserLoginRequest,
    UserRegistrationRequest,
)

from app.security.password import (
    hash_password,
    verify_password_and_update,
)

from app.services.auth_exceptions import (
    AuthenticationError,
)


logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication-related user account operations.
    """

    def register_user(
        self,
        db: Session,
        request: UserRegistrationRequest,
    ) -> User:
        """
        Register a new ScholarAI user.

        Passwords are hashed before database persistence.
        """

        normalized_email = (
            str(request.email).strip().casefold()
        )

        existing_user = db.scalar(
            select(User).where(
                User.email == normalized_email
            )
        )

        if existing_user is not None:

            raise ValueError(
                "An account with this email already exists."
            )

        password = request.password.get_secret_value()

        password_hash = hash_password(password)

        user = User(
            full_name=request.full_name,
            email=normalized_email,
            password_hash=password_hash,
            is_active=True,
        )

        try:

            db.add(user)

            db.commit()

            db.refresh(user)

            logger.info(
                "ScholarAI user registered successfully.",
                extra={
                    "user_id": str(user.id),
                },
            )

            return user

        except IntegrityError as exc:

            db.rollback()

            logger.warning(
                "Registration rejected due to database integrity conflict."
            )

            raise ValueError(
                "An account with this email already exists."
            ) from exc

        except Exception:

            db.rollback()

            logger.exception(
                "Unexpected failure during registration."
            )

            raise

    def authenticate_user(
        self,
        db: Session,
        request: UserLoginRequest,
    ) -> User:
        """
        Authenticate a registered user.

        Process:
        1. Normalize email.
        2. Retrieve the account.
        3. Verify the password.
        4. Reject inactive accounts.
        5. Upgrade outdated password hashes.
        6. Return the authenticated user.

        Raises:
            AuthenticationError: If authentication fails.
        """

        normalized_email = (
            str(request.email).strip().casefold()
        )

        # STEP 1: Retrieve the account.
        user = db.scalar(
            select(User).where(
                User.email == normalized_email
            )
        )

        # STEP 2: Reject unknown accounts.
        if user is None:

            raise AuthenticationError()

        # STEP 3: Reject accounts without a usable password hash.
        if not user.password_hash:

            raise AuthenticationError()

        password = request.password.get_secret_value()

        # STEP 4: Verify credentials and detect hash upgrades.
        try:

            verified, upgraded_hash = (
                verify_password_and_update(
                    password,
                    user.password_hash,
                )
            )

        except RuntimeError:

            logger.exception(
                "Password verification or hash upgrade failed."
            )

            raise

        if not verified:

            raise AuthenticationError()

        # STEP 5: Reject inactive accounts.
        if not user.is_active:

            raise AuthenticationError()

        # STEP 6: Persist upgraded hash when required.
        if upgraded_hash is not None:

            try:

                user.password_hash = upgraded_hash

                db.commit()

                db.refresh(user)

                logger.info(
                    "Password hash upgraded after successful login.",
                    extra={
                        "user_id": str(user.id),
                    },
                )

            except Exception:

                db.rollback()

                logger.exception(
                    "Failed to persist upgraded password hash."
                )

                raise RuntimeError(
                    "Unable to complete credential verification."
                )

        logger.info(
            "ScholarAI user credentials verified successfully.",
            extra={
                "user_id": str(user.id),
            },
        )

        return user


auth_service = AuthService()