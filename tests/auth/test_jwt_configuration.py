import pytest

from app.core.jwt_config import (
    JWTSettings,
)


def test_valid_jwt_configuration():

    settings = JWTSettings(

        secret_key="x" * 64,

        algorithm="HS256",

        access_token_expire_minutes=15,

        issuer="scholarai-api",

        audience="scholarai-client",

    )

    assert settings.algorithm == "HS256"

    assert settings.access_token_expire_minutes == 15


def test_jwt_configuration_rejects_missing_secret():

    with pytest.raises(ValueError):

        JWTSettings(

            secret_key="",

            algorithm="HS256",

            access_token_expire_minutes=15,

            issuer="scholarai-api",

            audience="scholarai-client",

        )


def test_jwt_configuration_rejects_weak_secret():

    with pytest.raises(ValueError):

        JWTSettings(

            secret_key="short",

            algorithm="HS256",

            access_token_expire_minutes=15,

            issuer="scholarai-api",

            audience="scholarai-client",

        )


def test_jwt_configuration_rejects_unsupported_algorithm():

    with pytest.raises(ValueError):

        JWTSettings(

            secret_key="x" * 64,

            algorithm="none",

            access_token_expire_minutes=15,

            issuer="scholarai-api",

            audience="scholarai-client",

        )


def test_jwt_configuration_rejects_invalid_expiration():

    with pytest.raises(ValueError):

        JWTSettings(

            secret_key="x" * 64,

            algorithm="HS256",

            access_token_expire_minutes=0,

            issuer="scholarai-api",

            audience="scholarai-client",

        )