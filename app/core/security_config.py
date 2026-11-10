"""Validated security and rate-limiting configuration for ScholarAI."""

from dataclasses import dataclass
import os


def _positive_int(name: str, default: int, *, maximum: int = 1_000_000) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if value <= 0 or value > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}.")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


@dataclass(frozen=True)
class SecuritySettings:
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    api_requests_per_window: int = 120
    login_requests_per_window: int = 5
    registration_requests_per_window: int = 5
    refresh_requests_per_window: int = 10
    rate_limit_max_keys: int = 50_000

    @classmethod
    def from_environment(cls) -> "SecuritySettings":
        return cls(
            rate_limit_enabled=_boolean("SCHOLARAI_RATE_LIMIT_ENABLED", True),
            rate_limit_window_seconds=_positive_int(
                "SCHOLARAI_RATE_LIMIT_WINDOW_SECONDS", 60, maximum=3600
            ),
            api_requests_per_window=_positive_int(
                "SCHOLARAI_API_RATE_LIMIT", 120
            ),
            login_requests_per_window=_positive_int(
                "SCHOLARAI_LOGIN_RATE_LIMIT", 5
            ),
            registration_requests_per_window=_positive_int(
                "SCHOLARAI_REGISTER_RATE_LIMIT", 5
            ),
            refresh_requests_per_window=_positive_int(
                "SCHOLARAI_REFRESH_RATE_LIMIT", 10
            ),
            rate_limit_max_keys=_positive_int(
                "SCHOLARAI_RATE_LIMIT_MAX_KEYS", 50_000
            ),
        )


security_settings = SecuritySettings.from_environment()
