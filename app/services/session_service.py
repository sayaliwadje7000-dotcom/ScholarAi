"""
Persistent session lifecycle and refresh-token rotation.
"""

import logging
import uuid

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession

from app.security.refresh_token import (
    hash_refresh_token,
    compare_refresh_token_hash,
    create_refresh_token,
    decode_refresh_token,
)

from app.security.token import create_access_token

from app.security.token_exceptions import (
    TokenValidationError,
)

logger = logging.getLogger(__name__)


class SessionError(Exception):
    pass


class SessionService:

    def create_session(
        self,
        db: Session,
        user: User,
    ):

        session_id = uuid.uuid4()

        refresh_token, refresh_jti, expires_at = (
            create_refresh_token(
                user_id=user.id,
                session_id=session_id,
            )
        )

        session = UserSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(
                refresh_token
            ),
            current_refresh_jti=refresh_jti,
            expires_at=expires_at,
        )

        try:

            db.add(session)
            db.flush()

            access_token, expires_in = create_access_token(
                user_id=user.id,
                session_id=session_id,
            )

            db.commit()
            db.refresh(session)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in,
                "refresh_expires_at": expires_at,
                "session": session,
            }

        except Exception:
            db.rollback()
            raise

    def rotate_refresh_token(
        self,
        db: Session,
        refresh_token: str,
    ):

        try:
            payload = decode_refresh_token(refresh_token)

        except TokenValidationError as exc:
            raise SessionError(
                "Invalid or expired refresh token."
            ) from exc

        session_id = uuid.UUID(payload["sid"])
        user_id = uuid.UUID(payload["sub"])
        supplied_jti = uuid.UUID(payload["jti"])

        try:

            session = db.scalar(
                select(UserSession)
                .where(UserSession.id == session_id)
                .with_for_update()
            )

            if session is None:
                raise SessionError(
                    "Invalid or expired refresh token."
                )

            # A validly signed old token indicates reuse.
            if session.current_refresh_jti != supplied_jti:

                if session.revoked_at is None:
                    session.revoked_at = datetime.now(
                        timezone.utc
                    )
                    session.revoke_reason = "refresh_token_reuse"

                db.commit()

                raise SessionError(
                    "Refresh token reuse detected. Session revoked."
                )

            if session.revoked_at is not None:
                raise SessionError(
                    "Session has been revoked."
                )

            now = datetime.now(timezone.utc)

            if session.expires_at <= now:
                session.revoked_at = now
                session.revoke_reason = "expired"
                db.commit()

                raise SessionError(
                    "Session has expired."
                )

            if not compare_refresh_token_hash(
                refresh_token,
                session.refresh_token_hash,
            ):
                raise SessionError(
                    "Invalid or expired refresh token."
                )

            user = db.scalar(
                select(User).where(
                    User.id == user_id
                )
            )

            if (
                user is None
                or not user.is_active
                or user.id != session.user_id
            ):
                raise SessionError(
                    "Invalid or expired refresh token."
                )

            new_refresh_token, new_jti, _ = (
                create_refresh_token(
                    user_id=user.id,
                    session_id=session.id,
                )
            )

            new_access_token, expires_in = (
                create_access_token(
                    user_id=user.id,
                    session_id=session.id,
                )
            )

            session.refresh_token_hash = hash_refresh_token(
                new_refresh_token
            )

            session.current_refresh_jti = new_jti
            session.last_used_at = now

            db.commit()

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_in": expires_in,
                "refresh_expires_at": session.expires_at,
            }

        except SessionError:
            if db.in_transaction():
                db.rollback()
            raise

        except Exception:
            db.rollback()
            logger.exception("Refresh-token rotation failed.")
            raise

    def revoke_session(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str = "logout",
    ) -> bool:

        session = db.scalar(
            select(UserSession)
            .where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
            )
            .with_for_update()
        )

        if session is None:
            return False

        if session.revoked_at is not None:
            return True

        session.revoked_at = datetime.now(timezone.utc)
        session.revoke_reason = reason

        db.commit()

        return True

    def revoke_all_sessions(
        self,
        db: Session,
        user_id: uuid.UUID,
        except_session_id: uuid.UUID | None = None,
    ) -> int:

        statement = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .with_for_update()
        )

        sessions = db.scalars(statement).all()

        now = datetime.now(timezone.utc)
        revoked_count = 0

        for session in sessions:

            if (
                except_session_id is not None
                and session.id == except_session_id
            ):
                continue

            session.revoked_at = now
            session.revoke_reason = "user_revoked_all"

            revoked_count += 1

        db.commit()

        return revoked_count

    def list_sessions(
        self,
        db: Session,
        user_id: uuid.UUID,
    ):

        return db.scalars(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc())
        ).all()


session_service = SessionService()
