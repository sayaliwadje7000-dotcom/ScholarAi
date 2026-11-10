import uuid

from datetime import datetime, timedelta, timezone

from app.security.refresh_token import (
    hash_refresh_token,
    compare_refresh_token_hash,
)


def test_refresh_token_hash_is_sha256_hex():

    token = "test-refresh-token"

    result = hash_refresh_token(token)

    assert len(result) == 64
    assert result == hash_refresh_token(token)


def test_refresh_token_hash_comparison():

    token = "test-refresh-token"

    hashed = hash_refresh_token(token)

    assert compare_refresh_token_hash(token, hashed)


def test_refresh_token_hash_rejects_wrong_token():

    hashed = hash_refresh_token("correct-token")

    assert not compare_refresh_token_hash(
        "incorrect-token",
        hashed,
    )


def test_refresh_token_hash_rejects_empty_token():

    import pytest

    with pytest.raises(ValueError):
        hash_refresh_token("")


def test_session_model_has_required_fields():

    from app.models.user_session import UserSession

    required_fields = {
        "id",
        "user_id",
        "refresh_token_hash",
        "current_refresh_jti",
        "created_at",
        "last_used_at",
        "expires_at",
        "revoked_at",
        "revoke_reason",
    }

    assert required_fields.issubset(
        set(UserSession.__table__.columns.keys())
    )
