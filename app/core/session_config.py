"""
Phase 18.6: Refresh token configuration.
"""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class SessionSettings:
    refresh_token_expire_days: int = 7

    @classmethod
    def from_environment(cls):
        days = int(
            os.getenv(
                "SCHOLARAI_REFRESH_TOKEN_EXPIRE_DAYS",
                "7",
            )
        )

        if days <= 0 or days > 90:
            raise ValueError(
                "Refresh token lifetime must be between 1 and 90 days."
            )

        return cls(refresh_token_expire_days=days)


def get_session_settings():
    return SessionSettings.from_environment()
