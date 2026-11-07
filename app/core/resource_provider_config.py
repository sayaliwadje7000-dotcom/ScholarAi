import os

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class ResourceProviderSettings:
    """
    Configuration for external educational resource providers.
    """

    youtube_api_key: str | None = None
    openalex_api_key: str | None = None
    crossref_mailto: str | None = None
    google_books_api_key: str | None = None

    enabled: bool = True

    timeout_seconds: float = 15.0
    max_retries: int = 2
    max_concurrency: int = 4

    base_retry_delay: float = 0.5
    max_retry_delay: float = 4.0

    max_results_per_provider: int = 20

    def __post_init__(self):

        if self.timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive."
            )

        if self.max_retries < 0:
            raise ValueError(
                "max_retries cannot be negative."
            )

        if self.max_concurrency < 1:
            raise ValueError(
                "max_concurrency must be at least 1."
            )

        if self.base_retry_delay < 0:
            raise ValueError(
                "base_retry_delay cannot be negative."
            )

        if self.max_retry_delay < self.base_retry_delay:
            raise ValueError(
                "max_retry_delay cannot be smaller "
                "than base_retry_delay."
            )

        if not 1 <= self.max_results_per_provider <= 100:
            raise ValueError(
                "max_results_per_provider must be "
                "between 1 and 100."
            )

    @classmethod
    def from_environment(cls):

        return cls(
            youtube_api_key=os.getenv(
                "YOUTUBE_API_KEY"
            ),

            openalex_api_key=os.getenv(
                "OPENALEX_API_KEY"
            ),

            crossref_mailto=os.getenv(
                "CROSSREF_MAILTO"
            ),

            google_books_api_key=os.getenv(
                "GOOGLE_BOOKS_API_KEY"
            ),

            enabled=os.getenv(
                "RESOURCE_DISCOVERY_ENABLED",
                "true",
            ).lower() == "true",

            timeout_seconds=float(
                os.getenv(
                    "RESOURCE_DISCOVERY_TIMEOUT_SECONDS",
                    "15",
                )
            ),

            max_retries=int(
                os.getenv(
                    "RESOURCE_DISCOVERY_MAX_RETRIES",
                    "2",
                )
            ),

            max_concurrency=int(
                os.getenv(
                    "RESOURCE_DISCOVERY_MAX_CONCURRENCY",
                    "4",
                )
            ),

            base_retry_delay=float(
                os.getenv(
                    "RESOURCE_DISCOVERY_BASE_RETRY_DELAY",
                    "0.5",
                )
            ),

            max_retry_delay=float(
                os.getenv(
                    "RESOURCE_DISCOVERY_MAX_RETRY_DELAY",
                    "4",
                )
            ),

            max_results_per_provider=int(
                os.getenv(
                    "RESOURCE_DISCOVERY_MAX_RESULTS",
                    "20",
                )
            ),
        )


@lru_cache(maxsize=1)
def get_resource_provider_settings():
    return ResourceProviderSettings.from_environment()