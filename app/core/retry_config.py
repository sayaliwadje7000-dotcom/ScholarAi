import math
import os

from dataclasses import dataclass

from app.core.document_config import (
    get_boolean,
    get_positive_integer,
)


def get_positive_float(
    name: str,
    default: float,
) -> float:
    """Read a positive finite floating-point environment variable."""

    raw_value = os.getenv(
        name,
        str(default),
    ).strip()

    try:
        value = float(raw_value)

    except ValueError as exc:
        raise ValueError(
            f"{name} must be a valid number."
        ) from exc

    if not math.isfinite(value) or value <= 0:
        raise ValueError(
            f"{name} must be a finite positive number."
        )

    return value


@dataclass(frozen=True)
class DocumentRetrySettings:
    """
    Central configuration for document-processing retries.

    max_attempts represents the total number of attempts,
    including the initial processing attempt.
    """

    enabled: bool

    max_attempts: int

    initial_delay_seconds: float

    backoff_multiplier: float

    max_delay_seconds: float


def load_document_retry_settings() -> DocumentRetrySettings:
    """Load and validate document retry configuration."""

    settings = DocumentRetrySettings(

        enabled=get_boolean(
            "DOCUMENT_RETRY_ENABLED",
            True,
        ),

        max_attempts=get_positive_integer(
            "DOCUMENT_MAX_PROCESSING_ATTEMPTS",
            3,
        ),

        initial_delay_seconds=get_positive_float(
            "DOCUMENT_RETRY_INITIAL_DELAY_SECONDS",
            5.0,
        ),

        backoff_multiplier=get_positive_float(
            "DOCUMENT_RETRY_BACKOFF_MULTIPLIER",
            2.0,
        ),

        max_delay_seconds=get_positive_float(
            "DOCUMENT_RETRY_MAX_DELAY_SECONDS",
            60.0,
        ),
    )

    if settings.backoff_multiplier < 1:
        raise ValueError(
            "DOCUMENT_RETRY_BACKOFF_MULTIPLIER "
            "must be greater than or equal to 1."
        )

    if settings.max_delay_seconds < settings.initial_delay_seconds:
        raise ValueError(
            "DOCUMENT_RETRY_MAX_DELAY_SECONDS "
            "cannot be smaller than the initial retry delay."
        )

    return settings


document_retry_settings = load_document_retry_settings()