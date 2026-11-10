"""
ScholarAI Refresh Token Service.
Phase 18.6.
"""

import uuid

from datetime import datetime, timedelta, timezone

import jwt

from app.core.jwt_config import jwt_settings
from app.core.session_config import get_session_settings

from app.security.token_exceptions import (
    TokenCreationError,
    TokenValidationError,
)


def hash_refresh_token(token: str) -> str:
    import hashlib

    if not isinstance(token, str) or not token:
        raise ValueError("Invalid refresh token.")

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def compare_refresh_token_hash(
    supplied_token: str,
    stored_hash: str,
) -> bool:
    import hmac

    return hmac.compare_digest(
        hash_refresh_token(supplied_token),
        stored_hash,
    )


def create_refresh_token(
    user_id: uuid.UUID,
    session_id: uuid.UUID,
):
    settings = get_session_settings()

    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(
        days=settings.refresh_token_expire_days
    )

    jti = uuid.uuid4()

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": str(jti),
        "type": "refresh",
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "iss": jwt_settings.issuer,
        "aud": jwt_settings.audience,
    }

    try:
        token = jwt.encode(
            payload,
            jwt_settings.secret_key,
            algorithm=jwt_settings.algorithm,
        )

        return token, jti, expires_at

    except Exception as exc:
        raise TokenCreationError(
            "Unable to create refresh token."
        ) from exc


def decode_refresh_token(token: str) -> dict:

    if not isinstance(token, str) or not token.strip():
        raise TokenValidationError("Invalid refresh token.")

    try:
        payload = jwt.decode(
            token,
            jwt_settings.secret_key,
            algorithms=[jwt_settings.algorithm],
            issuer=jwt_settings.issuer,
            audience=jwt_settings.audience,
            options={
                "require": [
                    "sub",
                    "sid",
                    "jti",
                    "type",
                    "iat",
                    "nbf",
                    "exp",
                    "iss",
                    "aud",
                ],
            },
        )

        if payload.get("type") != "refresh":
            raise TokenValidationError("Invalid token type.")

        uuid.UUID(payload["sub"])
        uuid.UUID(payload["sid"])
        uuid.UUID(payload["jti"])

        return payload

    except TokenValidationError:
        raise

    except Exception as exc:
        raise TokenValidationError(
            "Invalid or expired refresh token."
        ) from exc