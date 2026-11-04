import subprocess

import pytest

from app.services.document_error_service import (
    DocumentErrorCategory,
    classify_document_error,
    is_retryable_document_error,
)

from app.services.ocr_service import (
    OCRProcessingError,
    OCRConfigurationError,
)

from app.services.pdf_extraction_service import (
    PDFExtractionIntegrityError,
)


def test_timeout_is_retryable():

    error = subprocess.TimeoutExpired(
        cmd="tesseract",
        timeout=60,
    )

    result = classify_document_error(error)

    assert result.category == DocumentErrorCategory.TRANSIENT
    assert result.retryable is True


def test_wrapped_timeout_is_retryable():

    try:
        raise subprocess.TimeoutExpired(
            cmd="tesseract",
            timeout=60,
        )

    except subprocess.TimeoutExpired as cause:

        error = OCRProcessingError(
            "OCR processing failed."
        )

        error.__cause__ = cause

    assert is_retryable_document_error(error)


def test_corrupted_pdf_is_permanent():

    error = PDFExtractionIntegrityError(
        "Corrupted PDF."
    )

    result = classify_document_error(error)

    assert result.category == DocumentErrorCategory.PERMANENT
    assert not result.retryable


def test_invalid_ocr_configuration_is_permanent():

    error = OCRConfigurationError(
        "Invalid OCR configuration."
    )

    assert not is_retryable_document_error(error)


def test_unknown_error_is_permanent():

    error = RuntimeError(
        "Unknown processing failure."
    )

    result = classify_document_error(error)

    assert result.category == DocumentErrorCategory.PERMANENT


@pytest.mark.parametrize(
    "error",
    [
        ValueError("Invalid value"),
        TypeError("Invalid type"),
        FileNotFoundError("Missing file"),
        PermissionError("Access denied"),
    ],
)
def test_known_permanent_errors(error):

    assert not is_retryable_document_error(error)