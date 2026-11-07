import os

from dataclasses import dataclass
from functools import lru_cache


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"false", "0", "no", "off"}:
        return False

    raise ValueError(f"{name} must be a valid boolean value.")


@dataclass(frozen=True, slots=True)
class OpportunityProviderSettings:

    enabled: bool = False

    adzuna_enabled: bool = False
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    adzuna_country: str = "gb"

    timeout_seconds: float = 15.0
    max_retries: int = 2

    base_retry_delay: float = 0.5
    max_retry_delay: float = 4.0

    max_concurrency: int = 4
    max_results_per_provider: int = 20

    def __post_init__(self):

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative.")

        if self.base_retry_delay < 0:
            raise ValueError("base_retry_delay cannot be negative.")

        if self.max_retry_delay < self.base_retry_delay:
            raise ValueError("max_retry_delay cannot be smaller than base_retry_delay.")

        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1.")

        if not 1 <= self.max_results_per_provider <= 50:
            raise ValueError("max_results_per_provider must be between 1 and 50.")

        country = self.adzuna_country.strip().lower()

        if len(country) != 2 or not country.isalpha():
            raise ValueError("adzuna_country must be a two-letter country code.")

        object.__setattr__(self, "adzuna_country", country)

    @property
    def adzuna_configured(self) -> bool:
        return bool(self.adzuna_app_id and self.adzuna_app_key)

    @classmethod
    def from_environment(cls):

        return cls(
            enabled=_get_bool("OPPORTUNITY_DISCOVERY_ENABLED", False),
            adzuna_enabled=_get_bool("ADZUNA_PROVIDER_ENABLED", False),

            adzuna_app_id=os.getenv("ADZUNA_APP_ID"),
            adzuna_app_key=os.getenv("ADZUNA_APP_KEY"),

            adzuna_country=os.getenv("ADZUNA_COUNTRY", "gb"),

            timeout_seconds=float(os.getenv("OPPORTUNITY_TIMEOUT_SECONDS", "15")),
            max_retries=int(os.getenv("OPPORTUNITY_MAX_RETRIES", "2")),

            base_retry_delay=float(os.getenv("OPPORTUNITY_BASE_RETRY_DELAY", "0.5")),
            max_retry_delay=float(os.getenv("OPPORTUNITY_MAX_RETRY_DELAY", "4")),

            max_concurrency=int(os.getenv("OPPORTUNITY_MAX_CONCURRENCY", "4")),
            max_results_per_provider=int(os.getenv("OPPORTUNITY_MAX_RESULTS", "20")),
        )


@lru_cache(maxsize=1)
def get_opportunity_provider_settings():
    return OpportunityProviderSettings.from_environment()