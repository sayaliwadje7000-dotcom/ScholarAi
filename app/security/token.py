"""
ScholarAI JWT Access Token Service.

Phase 18.5: JWT access-token generation and validation.
Phase 18.6: Session-bound access tokens.

Responsibilities:
- Generate signed access tokens.
- Validate JWT signatures.
- Validate issuer and audience.
- Enforce token expiration.
- Validate token type and subject.
- Bind access tokens to persistent sessions.
- Return validated token claims.
"""

import logging

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from jwt.exceptions import InvalidTokenError

from app.core.jwt_config import jwt_settings

from app.security.token_exceptions import (
    TokenCreationError,
    TokenValidationError,
)


logger = logging.getLogger(__name__)

ACCESS_TOKEN_TYPE = "access"


def create_access_token(
    *,
    user_id: UUID | str,
    session_id: UUID | str | None = None,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    """
    Create a signed JWT access token.

    Args:
        user_id:
            Authenticated user's UUID.

        session_id:
            Persistent authentication session UUID.
            Optional for backward compatibility.

        expires_delta:
            Optional custom token lifetime.

    Returns:
        Tuple containing encoded JWT and expiration
        duration in seconds.
    """

    try:
        normalized_user_id = str(UUID(str(user_id)))

        normalized_session_id = (
            str(UUID(str(session_id)))
            if session_id is not None
            else None
        )

        now = datetime.now(timezone.utc)

        lifetime = (
            expires_delta
            if expires_delta is not None
            else timedelta(
                minutes=jwt_settings.access_token_expire_minutes
            )
        )

        if lifetime.total_seconds() <= 0:
            raise ValueError(
                "Token lifetime must be positive."
            )

        expires_at = now + lifetime

        claims = {
            "sub": normalized_user_id,
            "jti": str(uuid4()),
            "type": ACCESS_TOKEN_TYPE,
            "iat": now,
            "nbf": now,
            "exp": expires_at,
            "iss": jwt_settings.issuer,
            "aud": jwt_settings.audience,
        }

        # Phase 18.6: Bind token to persistent session.
        if normalized_session_id is not None:
            claims["sid"] = normalized_session_id

        encoded_token = jwt.encode(
            claims,
            jwt_settings.secret_key,
            algorithm=jwt_settings.algorithm,
        )

        expires_in = int(lifetime.total_seconds())

        return encoded_token, expires_in

    except Exception as exc:

        logger.exception(
            "Access-token creation failed."
        )

        raise TokenCreationError(
            "Unable to create access token."
        ) from exc


def decode_access_token(
    token: str,
) -> dict:
    """
    Decode and validate a JWT access token.

    Validation includes:
    - Signature verification.
    - Algorithm allowlisting.
    - Expiration.
    - Not-before timestamp.
    - Issuer.
    - Audience.
    - Required claims.
    - Access-token type.
    - UUID subject.
    - UUID token identifier.
    - Optional session identifier.
    """

    if not isinstance(token, str) or not token.strip():

        raise TokenValidationError(
            "Invalid access token."
        )

    try:

        claims = jwt.decode(
            token,
            jwt_settings.secret_key,
            algorithms=[
                jwt_settings.algorithm,
            ],
            issuer=jwt_settings.issuer,
            audience=jwt_settings.audience,
            options={
                "require": [
                    "sub",
                    "jti",
                    "type",
                    "iat",
                    "nbf",
                    "exp",
                    "iss",
                    "aud",
                ],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )

        if claims.get("type") != ACCESS_TOKEN_TYPE:

            raise TokenValidationError(
                "Invalid access-token type."
            )

        try:

            UUID(str(claims["sub"]))
            UUID(str(claims["jti"]))

            # Validate sid if present.
            if "sid" in claims:
                UUID(str(claims["sid"]))

        except (ValueError, TypeError, KeyError) as exc:

            raise TokenValidationError(
                "Invalid token identity claims."
            ) from exc

        return claims

    except TokenValidationError:
        raise

    except InvalidTokenError as exc:

        raise TokenValidationError(
            "Invalid or expired access token."
        ) from exc

    except Exception as exc:

        logger.exception(
            "Unexpected access-token validation failure."
        )

        raise TokenValidationError(
            "Unable to validate access token."
        ) from exc