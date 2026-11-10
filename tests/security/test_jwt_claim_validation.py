"""Phase 18.11: adversarial JWT claim-validation tests."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

os.environ.setdefault("SCHOLARAI_JWT_SECRET_KEY", secrets.token_urlsafe(48))

import jwt
import pytest

from app.core.jwt_config import jwt_settings
from app.security.token import ACCESS_TOKEN_TYPE, decode_access_token
from app.security.token_exceptions import TokenValidationError


def _signed_token(**overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
        "iss": jwt_settings.issuer,
        "aud": jwt_settings.audience,
    }
    claims.update(overrides)
    return jwt.encode(
        claims,
        jwt_settings.secret_key,
        algorithm=jwt_settings.algorithm,
    )


def test_rejects_wrong_issuer():
    with pytest.raises(TokenValidationError):
        decode_access_token(_signed_token(iss="attacker-controlled-issuer"))


def test_rejects_wrong_audience():
    with pytest.raises(TokenValidationError):
        decode_access_token(_signed_token(aud="another-application"))


@pytest.mark.parametrize("missing_claim", ["sub", "jti", "type", "iat", "nbf", "exp", "iss", "aud"])
def test_rejects_missing_required_claim(missing_claim):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
        "iss": jwt_settings.issuer,
        "aud": jwt_settings.audience,
    }
    claims.pop(missing_claim)
    token = jwt.encode(claims, jwt_settings.secret_key, algorithm=jwt_settings.algorithm)
    with pytest.raises(TokenValidationError):
        decode_access_token(token)


def test_rejects_malformed_session_id_when_present():
    with pytest.raises(TokenValidationError):
        decode_access_token(_signed_token(sid="not-a-uuid"))


def test_accepts_valid_session_bound_token():
    user_id, session_id = uuid4(), uuid4()
    token = _signed_token(sub=str(user_id), sid=str(session_id))
    claims = decode_access_token(token)
    assert claims["sub"] == str(user_id)
    assert claims["sid"] == str(session_id)
