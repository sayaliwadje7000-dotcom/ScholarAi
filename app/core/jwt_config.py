"""
ScholarAI JWT Configuration.

Centralizes access-token security settings.

The signing secret is never hard-coded.
Production deployments must provide it through
a secure environment variable or secret manager.
"""

import os

from dataclasses import dataclass


SUPPORTED_JWT_ALGORITHMS = {
    "HS256",
}


@dataclass(frozen=True)
class JWTSettings:

    secret_key: str

    algorithm: str

    access_token_expire_minutes: int

    issuer: str

    audience: str

    def __post_init__(self):

        if not self.secret_key:

            raise ValueError(
                "SCHOLARAI_JWT_SECRET_KEY is required."
            )

        if len(self.secret_key.encode("utf-8")) < 32:

            raise ValueError(
                "JWT secret must contain at least "
                "32 bytes."
            )

        if self.algorithm not in SUPPORTED_JWT_ALGORITHMS:

            raise ValueError(
                "Unsupported JWT signing algorithm."
            )

        if self.access_token_expire_minutes <= 0:

            raise ValueError(
                "JWT access-token expiration "
                "must be positive."
            )

        if not self.issuer.strip():

            raise ValueError(
                "JWT issuer cannot be empty."
            )

        if not self.audience.strip():

            raise ValueError(
                "JWT audience cannot be empty."
            )


def load_jwt_settings() -> JWTSettings:

    return JWTSettings(

        secret_key=os.getenv(
            "SCHOLARAI_JWT_SECRET_KEY",
            "",
        ).strip(),

        algorithm=os.getenv(
            "SCHOLARAI_JWT_ALGORITHM",
            "HS256",
        ).strip(),

        access_token_expire_minutes=int(
            os.getenv(
                "SCHOLARAI_JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
                "15",
            )
        ),

        issuer=os.getenv(
            "SCHOLARAI_JWT_ISSUER",
            "scholarai-api",
        ).strip(),

        audience=os.getenv(
            "SCHOLARAI_JWT_AUDIENCE",
            "scholarai-client",
        ).strip(),

    )


jwt_settings = load_jwt_settings()