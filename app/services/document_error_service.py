import errno
import logging
import socket
import subprocess

from enum import Enum

from sqlalchemy.exc import (
    DisconnectionError,
    OperationalError,
    TimeoutError as SQLAlchemyTimeoutError,
)

from app.services.pdf_extraction_service import (
    PDFExtractionError,
    PDFExtractionIntegrityError,
)

from app.services.ocr_service import (
    OCRError,
    OCRConfigurationError,
    OCRProcessingError,
)


logger = logging.getLogger(__name__)


# ==========================================================
# ERROR CLASSIFICATION
# ==========================================================

class DocumentErrorCategory(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class DocumentErrorClassification:
    """Structured document-processing error classification."""

    def __init__(
        self,
        category: DocumentErrorCategory,
        reason: str,
    ):
        self.category = category
        self.reason = reason

    @property
    def retryable(self) -> bool:
        return self.category == DocumentErrorCategory.TRANSIENT


# ==========================================================
# RETRYABLE ERROR DEFINITIONS
# ==========================================================

# Errors that may be temporary.
RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    socket.timeout,
    ConnectionError,
    subprocess.TimeoutExpired,
    DisconnectionError,
    SQLAlchemyTimeoutError,
)


# Selected operating-system errors that may be temporary.
RETRYABLE_ERRNO_VALUES = {
    errno.EAGAIN,
    errno.EINTR,
    errno.EBUSY,
    errno.ETIMEDOUT,
    errno.ECONNRESET,
    errno.ECONNREFUSED,
    errno.EHOSTUNREACH,
    errno.ENETUNREACH,
    errno.EPIPE,
}


# PostgreSQL SQLSTATE codes representing transient
# transaction, locking, or server availability failures.
TRANSIENT_SQLSTATE_CODES = {
    "40001",  # Serialization failure
    "40P01",  # Deadlock detected
    "55P03",  # Lock not available
    "57P01",  # Admin shutdown
    "57P02",  # Crash shutdown
    "57P03",  # Cannot connect now
}


# PostgreSQL connection exception class.
# SQLSTATE codes beginning with 08 indicate connection errors.
TRANSIENT_SQLSTATE_PREFIXES = ("08",)


# ==========================================================
# EXCEPTION CHAIN
# ==========================================================

def get_exception_chain(
    exc: Exception,
) -> list[Exception]:
    """Return the exception and its underlying causes."""

    chain = []
    visited = set()

    current = exc

    while current is not None and id(current) not in visited:

        visited.add(id(current))
        chain.append(current)

        current = (
            current.__cause__
            or current.__context__
        )

    return chain


# ==========================================================
# DATABASE ERROR CLASSIFICATION
# ==========================================================

def is_transient_database_error(
    exc: Exception,
) -> bool:
    """
    Determine whether a SQLAlchemy OperationalError
    represents a recognized transient PostgreSQL failure.

    Unknown OperationalError instances are not automatically
    considered retryable.
    """

    if not isinstance(exc, OperationalError):
        return False

    original_error = getattr(exc, "orig", None)

    if original_error is None:
        return False

    sqlstate = (
        getattr(original_error, "sqlstate", None)
        or getattr(original_error, "pgcode", None)
    )

    if not isinstance(sqlstate, str):
        return False

    return (
        sqlstate in TRANSIENT_SQLSTATE_CODES
        or sqlstate.startswith(TRANSIENT_SQLSTATE_PREFIXES)
    )


# ==========================================================
# DOCUMENT ERROR CLASSIFICATION
# ==========================================================

def classify_document_error(
    exc: Exception,
) -> DocumentErrorClassification:
    """
    Classify document-processing errors.

    Classification rules:

    1. Known temporary infrastructure errors are transient.
    2. Selected operating-system errors are transient.
    3. Recognized PostgreSQL transient errors are transient.
    4. Invalid documents and configuration errors are permanent.
    5. Unknown errors are permanent by default.
    """

    chain = get_exception_chain(exc)

    # Inspect the deepest underlying exception first.
    for current in reversed(chain):

        # --------------------------------------------------
        # 1. Known transient infrastructure errors
        # --------------------------------------------------

        if isinstance(current, RETRYABLE_EXCEPTIONS):

            return DocumentErrorClassification(
                DocumentErrorCategory.TRANSIENT,
                type(current).__name__,
            )

        # --------------------------------------------------
        # 2. Transient database errors
        # --------------------------------------------------

        if is_transient_database_error(current):

            return DocumentErrorClassification(
                DocumentErrorCategory.TRANSIENT,
                "Transient database error.",
            )

        # --------------------------------------------------
        # 3. Selected transient operating-system errors
        # --------------------------------------------------

        if isinstance(current, OSError):

            if current.errno in RETRYABLE_ERRNO_VALUES:

                return DocumentErrorClassification(
                    DocumentErrorCategory.TRANSIENT,
                    (
                        "Temporary operating-system error: "
                        f"{current.errno}"
                    ),
                )

        # --------------------------------------------------
        # 4. Permanent document-processing errors
        # --------------------------------------------------

        if isinstance(
            current,
            (
                FileNotFoundError,
                PermissionError,
                ValueError,
                TypeError,
                UnicodeError,
                PDFExtractionIntegrityError,
                PDFExtractionError,
                OCRConfigurationError,
                OCRProcessingError,
                OCRError,
            ),
        ):

            return DocumentErrorClassification(
                DocumentErrorCategory.PERMANENT,
                type(current).__name__,
            )

    # ------------------------------------------------------
    # 5. Unknown errors default to permanent
    # ------------------------------------------------------

    logger.warning(
        "Unrecognized document-processing error classified "
        "as permanent: %s",
        type(exc).__name__,
    )

    return DocumentErrorClassification(
        DocumentErrorCategory.PERMANENT,
        "Unrecognized processing error.",
    )


# ==========================================================
# RETRY ELIGIBILITY HELPER
# ==========================================================

def is_retryable_document_error(
    exc: Exception,
) -> bool:
    """Return whether an exception is eligible for retry."""

    return classify_document_error(exc).retryable