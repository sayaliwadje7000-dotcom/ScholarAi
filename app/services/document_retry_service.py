import logging
import time

from typing import Callable

from sqlalchemy.orm import Session

from app.core.document_config import DocumentSettings
from app.core.ocr_config import OCRSettings

from app.core.retry_config import (
    DocumentRetrySettings,
    document_retry_settings,
)

from app.services.document_processing_service import (
    DocumentProcessingResult,
    DocumentProcessingAlreadyClaimedError,
    process_document,
)

from app.services.document_error_service import (
    classify_document_error,
)


logger = logging.getLogger(__name__)


# ============================================================
# EXCEPTIONS
# ============================================================

class DocumentRetryError(Exception):
    """Base exception for document retry operations."""


class RetryLimitExceededError(DocumentRetryError):
    """Raised when maximum processing attempts are exhausted."""


# ============================================================
# RETRY ELIGIBILITY
# ============================================================

def can_retry_document(
    document,
    settings: DocumentRetrySettings | None = None,
) -> bool:

    if settings is None:
        settings = document_retry_settings

    if not settings.enabled:
        return False

    if document.processing_status != "failed":
        return False

    attempts = (
        getattr(document, "processing_attempts", 0) or 0
    )

    return attempts < settings.max_attempts


# ============================================================
# BACKOFF CALCULATION
# ============================================================

def calculate_retry_delay(
    failed_attempts: int,
    settings: DocumentRetrySettings | None = None,
) -> float:

    if settings is None:
        settings = document_retry_settings

    if (
        not isinstance(failed_attempts, int)
        or isinstance(failed_attempts, bool)
        or failed_attempts < 1
    ):
        raise ValueError(
            "failed_attempts must be a positive integer."
        )

    delay = (
        settings.initial_delay_seconds
        * settings.backoff_multiplier ** (failed_attempts - 1)
    )

    return min(
        delay,
        settings.max_delay_seconds,
    )


# ============================================================
# RETRY EXECUTION
# ============================================================

def process_document_with_retries(
    *,
    document_record,
    pdf_path,
    db: Session,
    document_settings: DocumentSettings,
    ocr_settings: OCRSettings,
    retry_settings: DocumentRetrySettings | None = None,
    sleep_function: Callable[[float], None] = time.sleep,
) -> DocumentProcessingResult:

    if retry_settings is None:
        retry_settings = document_retry_settings

    initial_attempts = (
        getattr(
            document_record,
            "processing_attempts",
            0,
        ) or 0
    )

    if initial_attempts >= retry_settings.max_attempts:
        raise RetryLimitExceededError(
            "Maximum document-processing attempts have "
            "already been exhausted."
        )

    attempts_this_execution = 0

    while True:

        try:
            result = process_document(
                document_record=document_record,
                pdf_path=pdf_path,
                db=db,
                document_settings=document_settings,
                ocr_settings=ocr_settings,
            )

            logger.info(
                "Document %s completed after %s attempt(s).",
                document_record.id,
                attempts_this_execution + 1,
            )

            return result

        except DocumentProcessingAlreadyClaimedError:
            # Another worker owns this document.
            # Never retry or mark its processing as failed.
            raise

        except Exception as exc:

            attempts_this_execution += 1

            attempts_used = (
                initial_attempts
                + attempts_this_execution
            )

            classification = classify_document_error(exc)

            logger.error(
                "Document %s failed on attempt %s. "
                "Category: %s. Reason: %s.",
                document_record.id,
                attempts_used,
                classification.category.value,
                classification.reason,
            )

            if not retry_settings.enabled:
                raise

            if not classification.retryable:
                logger.error(
                    "Document %s will not be retried.",
                    document_record.id,
                )
                raise

            if attempts_used >= retry_settings.max_attempts:
                raise RetryLimitExceededError(
                    "Maximum document-processing attempts exhausted."
                ) from exc

            delay = calculate_retry_delay(
                failed_attempts=attempts_used,
                settings=retry_settings,
            )

            logger.warning(
                "Retrying document %s after %.2f seconds. "
                "Next attempt: %s.",
                document_record.id,
                delay,
                attempts_used + 1,
            )

            sleep_function(delay)