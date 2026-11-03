import json
import os
import tempfile

from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from uuid import UUID

import pymupdf
import pytesseract

from PIL import Image

from pytesseract import Output

from app.core.ocr_config import OCRSettings

from app.services.pdf_extraction_service import (
    normalize_extracted_text,
)


class OCRError(Exception):
    """Base exception for OCR processing errors."""


class OCRConfigurationError(OCRError):
    """Raised when OCR configuration is invalid."""


class OCRProcessingError(OCRError):
    """Raised when OCR processing fails."""


class OCRStorageError(OCRError):
    """Raised when OCR output cannot be saved."""


@dataclass(frozen=True)
class OCRPageResult:
    page_number: int
    text: str
    extraction_method: str
    ocr_status: str
    character_count: int
    word_count: int
    average_confidence: float | None
    low_confidence: bool
    warnings: list[str]


@dataclass(frozen=True)
class OCRDocumentResult:
    document_id: str
    page_count: int
    pages_with_text: int
    total_characters: int
    total_words: int
    average_ocr_confidence: float | None
    quality_status: str
    ocr_pages: list[int]
    failed_pages: list[int]
    warnings: list[str]
    pages: list[OCRPageResult]


def configure_tesseract(settings: OCRSettings) -> None:
    """Configure the local Tesseract executable."""

    executable = Path(settings.tesseract_cmd)

    if not executable.is_file():
        raise OCRConfigurationError(
            "Tesseract executable was not found. "
            "Check TESSERACT_CMD in your environment."
        )

    pytesseract.pytesseract.tesseract_cmd = str(
        executable
    )


def validate_ocr_language(
    settings: OCRSettings,
) -> None:
    """Check whether the requested language data is available."""

    try:
        available_languages = (
            pytesseract.get_languages(config="")
        )

    except Exception as exc:
        raise OCRConfigurationError(
            "Unable to read installed Tesseract languages."
        ) from exc

    requested_languages = settings.language.split("+")

    missing_languages = [
        language
        for language in requested_languages
        if language not in available_languages
    ]

    if missing_languages:
        raise OCRConfigurationError(
            "Missing Tesseract language data: "
            + ", ".join(missing_languages)
        )


def render_pdf_page(
    page,
    dpi: int,
) -> Image.Image:
    """Render a PDF page as an RGB image."""

    scale = dpi / 72

    matrix = pymupdf.Matrix(
        scale,
        scale,
    )

    try:
        pixmap = page.get_pixmap(
            matrix=matrix,
            colorspace=pymupdf.csRGB,
            alpha=False,
        )

        image = Image.frombytes(
            "RGB",
            [pixmap.width, pixmap.height],
            pixmap.samples,
        )

        return image

    except Exception as exc:
        raise OCRProcessingError(
            "Failed to render PDF page."
        ) from exc


def extract_text_with_ocr(
    image: Image.Image,
    settings: OCRSettings,
) -> tuple[str, float | None]:
    """
    Extract text and confidence information using Tesseract.

    Confidence is calculated from valid word-level confidence
    scores returned by Tesseract.
    """

    try:
        data = pytesseract.image_to_data(
            image,
            lang=settings.language,
            config="--oem 3 --psm 3",
            output_type=Output.DICT,
            timeout=settings.timeout_seconds,
        )

    except Exception as exc:
        raise OCRProcessingError(
            "Tesseract failed to process the rendered page."
        ) from exc

    words = []
    confidence_values = []

    for text, confidence in zip(
        data["text"],
        data["conf"],
    ):

        text = text.strip()

        if not text:
            continue

        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            continue

        if confidence < 0:
            continue

        words.append(text)
        confidence_values.append(confidence)

    extracted_text = normalize_extracted_text(
        " ".join(words)
    )

    average_confidence = (
        round(mean(confidence_values), 2)
        if confidence_values
        else None
    )

    return extracted_text, average_confidence


def calculate_page_word_count(text: str) -> int:

    if not text.strip():
        return 0

    return len(text.split())


def process_pdf_page(
    page,
    page_number: int,
    settings: OCRSettings,
) -> OCRPageResult:
    """
    Process one page.

    Native text is preferred unless force_ocr is enabled.
    OCR is applied when native text is unavailable.
    """

    warnings = []

    try:
        native_text = normalize_extracted_text(
            page.get_text("text", sort=True)
        )

    except Exception as exc:
        raise OCRProcessingError(
            f"Native extraction failed on page {page_number}."
        ) from exc

    if native_text and not settings.force_ocr:

        return OCRPageResult(
            page_number=page_number,
            text=native_text,
            extraction_method="native",
            ocr_status="not_required",
            character_count=len(native_text),
            word_count=calculate_page_word_count(
                native_text
            ),
            average_confidence=None,
            low_confidence=False,
            warnings=[],
        )

    image = render_pdf_page(
        page,
        settings.dpi,
    )

    try:
        ocr_text, confidence = extract_text_with_ocr(
            image,
            settings,
        )

    finally:
        image.close()

    if not ocr_text:

        warnings.append(
            "OCR did not identify readable text on this page."
        )

        return OCRPageResult(
            page_number=page_number,
            text="",
            extraction_method="ocr",
            ocr_status="no_text",
            character_count=0,
            word_count=0,
            average_confidence=confidence,
            low_confidence=True,
            warnings=warnings,
        )

    low_confidence = (
        confidence is None
        or confidence < settings.minimum_confidence
    )

    if low_confidence:

        warnings.append(
            "OCR confidence is below the configured threshold."
        )

    return OCRPageResult(
        page_number=page_number,
        text=ocr_text,
        extraction_method="ocr",
        ocr_status="completed",
        character_count=len(ocr_text),
        word_count=calculate_page_word_count(
            ocr_text
        ),
        average_confidence=confidence,
        low_confidence=low_confidence,
        warnings=warnings,
    )


def determine_ocr_document_quality(
    pages: list[OCRPageResult],
) -> tuple[str, list[int], list[int], list[str]]:
    """Determine the overall OCR quality status."""

    warnings = []

    ocr_pages = [
        page.page_number
        for page in pages
        if page.extraction_method == "ocr"
    ]

    failed_pages = [
        page.page_number
        for page in pages
        if page.ocr_status == "failed"
    ]

    pages_with_text = [
        page
        for page in pages
        if page.text.strip()
    ]

    pages_without_text = [
        page.page_number
        for page in pages
        if not page.text.strip()
    ]

    for page in pages:

        for warning in page.warnings:

            warnings.append(
                f"Page {page.page_number}: {warning}"
            )

    if not pages_with_text:

        if failed_pages:
            return (
                "ocr_failed",
                ocr_pages,
                failed_pages,
                warnings,
            )

        return (
            "needs_ocr",
            ocr_pages,
            failed_pages,
            warnings,
        )

    if failed_pages or pages_without_text or any(
        page.low_confidence
        for page in pages
    ):

        return (
            "partial",
            ocr_pages,
            failed_pages,
            warnings,
        )

    return (
        "good",
        ocr_pages,
        failed_pages,
        warnings,
    )


def extract_pdf_with_ocr(
    pdf_path: Path,
    document_id: str,
    settings: OCRSettings,
    max_pages: int = 100,
) -> OCRDocumentResult:
    """
    Process a complete PDF using native extraction and OCR.

    Supports:
    - Native text PDFs
    - Scanned PDFs
    - Mixed PDFs
    """

    try:
        document_uuid = UUID(str(document_id))

    except (ValueError, TypeError, AttributeError) as exc:

        raise OCRProcessingError(
            "A valid document UUID is required."
        ) from exc

    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():

        raise OCRProcessingError(
            "The PDF file does not exist."
        )

    configure_tesseract(settings)

    validate_ocr_language(settings)

    try:
        pdf = pymupdf.open(
            filename=str(pdf_path)
        )

    except Exception as exc:

        raise OCRProcessingError(
            "Unable to open the PDF."
        ) from exc

    extracted_pages = []

    try:

        with pdf:

            if pdf.is_encrypted:

                raise OCRProcessingError(
                    "Encrypted PDFs cannot be processed."
                )

            if pdf.page_count <= 0:

                raise OCRProcessingError(
                    "The PDF does not contain any pages."
                )

            if pdf.page_count > max_pages:

                raise OCRProcessingError(
                    "The PDF exceeds the configured page limit."
                )

            for index in range(pdf.page_count):

                page = pdf.load_page(index)

                page_number = index + 1

                try:

                    page_result = process_pdf_page(
                        page=page,
                        page_number=page_number,
                        settings=settings,
                    )

                except OCRProcessingError as exc:

                    page_result = OCRPageResult(
                        page_number=page_number,
                        text="",
                        extraction_method="ocr",
                        ocr_status="failed",
                        character_count=0,
                        word_count=0,
                        average_confidence=None,
                        low_confidence=True,
                        warnings=[str(exc)],
                    )

                extracted_pages.append(
                    page_result
                )

    except OCRProcessingError:
        raise

    except Exception as exc:

        raise OCRProcessingError(
            "Unexpected PDF processing error."
        ) from exc

    total_characters = sum(
        page.character_count
        for page in extracted_pages
    )

    total_words = sum(
        page.word_count
        for page in extracted_pages
    )

    pages_with_text = sum(
        bool(page.text.strip())
        for page in extracted_pages
    )

    confidence_values = [
        page.average_confidence
        for page in extracted_pages
        if page.average_confidence is not None
    ]

    document_confidence = (
        round(mean(confidence_values), 2)
        if confidence_values
        else None
    )

    (
        quality_status,
        ocr_pages,
        failed_pages,
        warnings,
    ) = determine_ocr_document_quality(
        extracted_pages
    )

    return OCRDocumentResult(
        document_id=str(document_uuid),
        page_count=len(extracted_pages),
        pages_with_text=pages_with_text,
        total_characters=total_characters,
        total_words=total_words,
        average_ocr_confidence=document_confidence,
        quality_status=quality_status,
        ocr_pages=ocr_pages,
        failed_pages=failed_pages,
        warnings=warnings,
        pages=extracted_pages,
    )


def save_ocr_artifact(
    result: OCRDocumentResult,
    storage_root: Path,
) -> Path:
    """Save OCR results as a JSON artifact."""

    try:
        document_uuid = UUID(result.document_id)

    except (ValueError, TypeError, AttributeError) as exc:

        raise OCRStorageError(
            "Invalid document UUID."
        ) from exc

    processed_directory = (
        Path(storage_root) / "processed"
    )

    temporary_path = None

    try:

        processed_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            processed_directory
            / f"{document_uuid}_ocr.json"
        )

        payload = asdict(result)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix=f"{document_uuid}_",
            dir=processed_directory,
            delete=False,
        ) as temporary_file:

            temporary_path = Path(
                temporary_file.name
            )

            json.dump(
                payload,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )

            temporary_file.flush()

            os.fsync(
                temporary_file.fileno()
            )

        os.replace(
            temporary_path,
            destination,
        )

        return destination

    except Exception as exc:

        if temporary_path is not None:

            try:
                temporary_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

        raise OCRStorageError(
            "Unable to save OCR artifact."
        ) from exc


def process_pdf_ocr(
    pdf_path: Path,
    document_id: str,
    settings: OCRSettings,
    storage_root: Path,
    max_pages: int = 100,
) -> tuple[OCRDocumentResult, Path]:
    """Complete OCR processing and artifact generation."""

    result = extract_pdf_with_ocr(
        pdf_path=pdf_path,
        document_id=document_id,
        settings=settings,
        max_pages=max_pages,
    )

    artifact_path = save_ocr_artifact(
        result=result,
        storage_root=storage_root,
    )

    return result, artifact_path