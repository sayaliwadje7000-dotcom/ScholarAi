"""
Tests for ScholarAI JWT access-token functionality.

Phase 18.5:
- Token creation.
- Required claims.
- Signature verification.
- Expiration validation.
- Token type validation.
- Identity claim validation.
- Invalid lifetime rejection.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.core.jwt_config import jwt_settings

from app.security.token import (
    ACCESS_TOKEN_TYPE,
    create_access_token,
    decode_access_token,
)

from app.security.token_exceptions import (
    TokenCreationError,
    TokenValidationError,
)


def test_access_token_creation():

    user_id = uuid4()

    token, expires_in = create_access_token(
        user_id=user_id,
    )

    assert isinstance(token, str)
    assert len(token) > 0

    assert expires_in == (
        jwt_settings.access_token_expire_minutes * 60
    )


def test_access_token_contains_required_claims():

    user_id = uuid4()

    token, _ = create_access_token(
        user_id=user_id,
    )

    claims = decode_access_token(token)

    assert claims["sub"] == str(user_id)

    assert claims["type"] == ACCESS_TOKEN_TYPE

    assert "jti" in claims
    assert "iat" in claims
    assert "nbf" in claims
    assert "exp" in claims
    assert "iss" in claims
    assert "aud" in claims

    assert claims["iss"] == jwt_settings.issuer
    assert claims["aud"] == jwt_settings.audience


def test_access_token_rejects_invalid_signature():

    token, _ = create_access_token(
        user_id=uuid4(),
    )

    tampered_token = token[:-5] + "abcde"

    with pytest.raises(TokenValidationError):
        decode_access_token(tampered_token)


def test_access_token_rejects_expired_token():

    now = datetime.now(timezone.utc)

    claims = {
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now - timedelta(minutes=10),
        "nbf": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=5),
        "iss": jwt_settings.issuer,
        "aud": jwt_settings.audience,
    }

    expired_token = jwt.encode(
        claims,
        jwt_settings.secret_key,
        algorithm=jwt_settings.algorithm,
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(expired_token)


def test_access_token_rejects_empty_token():

    with pytest.raises(TokenValidationError):
        decode_access_token("")


def test_access_token_rejects_whitespace_token():

    with pytest.raises(TokenValidationError):
        decode_access_token("   ")


def test_access_token_rejects_invalid_token_type():

    now = datetime.now(timezone.utc)

    claims = {
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "type": "refresh",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=15),
        "iss": jwt_settings.issuer,
        "aud": jwt_settings.audience,
    }

    invalid_token = jwt.encode(
        claims,
        jwt_settings.secret_key,
        algorithm=jwt_settings.algorithm,
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(invalid_token)


def test_access_token_rejects_non_uuid_subject():

    now = datetime.now(timezone.utc)

    claims = {
        "sub": "invalid-user-id",
        "jti": str(uuid4()),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=15),
        "iss": jwt_settings.issuer,
        "aud": jwt_settings.audience,
    }

    invalid_token = jwt.encode(
        claims,
        jwt_settings.secret_key,
        algorithm=jwt_settings.algorithm,
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(invalid_token)


def test_access_token_rejects_non_uuid_token_identifier():

    now = datetime.now(timezone.utc)

    claims = {
        "sub": str(uuid4()),
        "jti": "invalid-token-id",
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=15),
        "iss": jwt_settings.issuer,
        "aud": jwt_settings.audience,
    }

    invalid_token = jwt.encode(
        claims,
        jwt_settings.secret_key,
        algorithm=jwt_settings.algorithm,
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(invalid_token)


@pytest.mark.parametrize(
    "lifetime",
    [
        timedelta(seconds=0),
        timedelta(seconds=-1),
    ],
)
def test_access_token_rejects_non_positive_lifetime(lifetime):

    with pytest.raises(TokenCreationError):
        create_access_token(
            user_id=uuid4(),
            expires_delta=lifetime,
        )


def test_access_token_accepts_custom_positive_lifetime():

    custom_lifetime = timedelta(minutes=30)

    token, expires_in = create_access_token(
        user_id=uuid4(),
        expires_delta=custom_lifetime,
    )

    assert isinstance(token, str)
    assert expires_in == 1800

    claims = decode_access_token(token)

    assert claims["type"] == ACCESS_TOKEN_TYPE