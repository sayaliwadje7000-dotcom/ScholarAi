import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class EmbeddingSettings:
    provider: str = "gemini"
    model: str = "gemini-embedding-2"
    dimensions: int = 1536

    api_key: str | None = None

    request_timeout_seconds: float = 30.0

    max_retries: int = 3
    retry_base_delay_seconds: float = 0.5
    retry_max_delay_seconds: float = 8.0

    max_concurrent_requests: int = 5

    max_input_characters: int = 100_000

    def __post_init__(self):
        if self.provider != "gemini":
            raise ValueError("Unsupported embedding provider.")

        if not self.model.strip():
            raise ValueError("Embedding model cannot be empty.")

        if self.dimensions not in (768, 1536, 3072):
         raise ValueError(
        "Embedding dimensions must be 768, 1536, or 3072."
    )
        if self.request_timeout_seconds <= 0:
            raise ValueError("Request timeout must be positive.")

        if self.max_retries < 0:
            raise ValueError("Maximum retries cannot be negative.")

        if self.retry_base_delay_seconds < 0:
            raise ValueError("Retry base delay cannot be negative.")

        if self.retry_max_delay_seconds < self.retry_base_delay_seconds:
            raise ValueError(
                "Maximum retry delay must be >= base retry delay."
            )

        if self.max_concurrent_requests < 1:
            raise ValueError(
                "Maximum concurrent requests must be at least 1."
            )

        if self.max_input_characters < 1:
            raise ValueError(
                "Maximum input characters must be positive."
            )

    @classmethod
    def from_environment(cls):
        return cls(
            provider=os.getenv(
                "EMBEDDING_PROVIDER",
                "gemini"
            ).strip().lower(),

            model=os.getenv(
                "EMBEDDING_MODEL",
                "gemini-embedding-2"
            ).strip(),

            dimensions=int(
                os.getenv("EMBEDDING_DIMENSIONS", "1536")
            ),

            api_key=os.getenv("GEMINI_API_KEY"),

            request_timeout_seconds=float(
                os.getenv(
                    "EMBEDDING_TIMEOUT_SECONDS",
                    "30"
                )
            ),

            max_retries=int(
                os.getenv(
                    "EMBEDDING_MAX_RETRIES",
                    "3"
                )
            ),

            retry_base_delay_seconds=float(
                os.getenv(
                    "EMBEDDING_RETRY_BASE_DELAY",
                    "0.5"
                )
            ),

            retry_max_delay_seconds=float(
                os.getenv(
                    "EMBEDDING_RETRY_MAX_DELAY",
                    "8"
                )
            ),

            max_concurrent_requests=int(
                os.getenv(
                    "EMBEDDING_MAX_CONCURRENCY",
                    "5"
                )
            ),

            max_input_characters=int(
                os.getenv(
                    "EMBEDDING_MAX_INPUT_CHARACTERS",
                    "100000"
                )
            ),
        )


@lru_cache(maxsize=1)
def get_embedding_settings() -> EmbeddingSettings:
    return EmbeddingSettings.from_environment()