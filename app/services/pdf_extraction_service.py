import json
import os
import tempfile
import unicodedata

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import pymupdf

from app.core.document_config import DocumentSettings


class PDFExtractionError(Exception):
    """Base exception for PDF extraction errors."""


class PDFExtractionIntegrityError(PDFExtractionError):
    """Raised when a PDF cannot be safely or correctly extracted."""


class PDFExtractionStorageError(PDFExtractionError):
    """Raised when an extraction artifact cannot be stored."""


@dataclass(frozen=True)
class PageExtractionResult:
    page_number: int
    text: str
    width: float
    height: float
    rotation: int
    character_count: int
    word_count: int
    is_empty: bool
    warnings: list[str]


@dataclass(frozen=True)
class PDFExtractionResult:
    document_id: str
    page_count: int
    total_characters: int
    total_words: int
    pages_with_text: int
    empty_pages: list[int]
    quality_status: str
    warnings: list[str]
    pages: list[PageExtractionResult]


def normalize_extracted_text(text: str) -> str:
    """
    Normalize extracted PDF text without destroying its structure.

    - Normalize Unicode.
    - Normalize line endings.
    - Remove null characters.
    - Remove unwanted control characters.
    - Normalize horizontal whitespace.
    - Preserve paragraph and line breaks.
    """

    if not isinstance(text, str):
        raise TypeError("Extracted text must be a string.")

    text = unicodedata.normalize("NFC", text)

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("\x00", "")

    cleaned_lines = []

    for line in text.split("\n"):
        cleaned_characters = []

        for character in line:
            if character == "\t":
                cleaned_characters.append(" ")
            elif unicodedata.category(character) == "Cc":
                continue
            else:
                cleaned_characters.append(character)

        cleaned_line = "".join(cleaned_characters)

        # Collapse repeated horizontal whitespace.
        cleaned_line = " ".join(cleaned_line.split())

        cleaned_lines.append(cleaned_line)

    normalized = "\n".join(cleaned_lines)

    return normalized.strip()


def calculate_word_count(text: str) -> int:
    """Calculate the number of whitespace-separated words."""

    if not text.strip():
        return 0

    return len(text.split())


def analyze_page_quality(text: str) -> list[str]:
    """Identify potential extraction quality problems."""

    warnings = []

    if not text.strip():
        warnings.append("No extractable text found on this page.")

    replacement_count = text.count("\ufffd")

    if replacement_count:
        warnings.append(
            "Text contains Unicode replacement characters."
        )

    if text.strip() and replacement_count / len(text) > 0.05:
        warnings.append(
            "A significant portion of the extracted text may be corrupted."
        )

    return warnings


def extract_page(
    page: Any,
    page_number: int,
) -> PageExtractionResult:
    """Extract and analyze one PDF page."""

    try:
        raw_text = page.get_text("text", sort=True)

    except Exception as exc:
        raise PDFExtractionIntegrityError(
            f"Failed to extract text from page {page_number}."
        ) from exc

    normalized_text = normalize_extracted_text(raw_text)

    word_count = calculate_word_count(normalized_text)

    warnings = analyze_page_quality(normalized_text)

    rectangle = page.rect

    return PageExtractionResult(
        page_number=page_number,
        text=normalized_text,
        width=round(float(rectangle.width), 2),
        height=round(float(rectangle.height), 2),
        rotation=int(page.rotation),
        character_count=len(normalized_text),
        word_count=word_count,
        is_empty=not bool(normalized_text.strip()),
        warnings=warnings,
    )


def determine_document_quality(
    pages: list[PageExtractionResult],
) -> tuple[str, list[str]]:
    """
    Determine overall extraction quality.

    good:
        All pages contain extractable text without warnings.

    partial:
        Some pages are empty or have extraction warnings.

    needs_ocr:
        No page contains extractable text.
    """

    document_warnings = []

    empty_pages = [
        page.page_number
        for page in pages
        if page.is_empty
    ]

    pages_with_text = [
        page
        for page in pages
        if not page.is_empty
    ]

    if not pages_with_text:
        document_warnings.append(
            "No extractable text was found. OCR may be required."
        )

        return "needs_ocr", document_warnings

    if empty_pages:
        document_warnings.append(
            f"Empty pages detected: {empty_pages}"
        )

    for page in pages:
        if page.warnings and not page.is_empty:
            document_warnings.append(
                f"Page {page.page_number}: "
                + " ".join(page.warnings)
            )

    if empty_pages or any(
        page.warnings for page in pages
    ):
        return "partial", document_warnings

    return "good", document_warnings


def extract_pdf_text(
    pdf_path: Path,
    document_id: str,
    settings: DocumentSettings,
) -> PDFExtractionResult:
    """
    Extract text from a stored PDF, page by page.

    The input PDF is never modified.
    """

    try:
        document_uuid = UUID(str(document_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise PDFExtractionError(
            "A valid document UUID is required."
        ) from exc

    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():
        raise PDFExtractionError(
            "The stored PDF file does not exist."
        )

    try:
        pdf_bytes = pdf_path.read_bytes()
    except OSError as exc:
        raise PDFExtractionError(
            "Unable to read the stored PDF file."
        ) from exc

    if not pdf_bytes:
        raise PDFExtractionIntegrityError(
            "The PDF file is empty."
        )

    try:
        pdf = pymupdf.open(
            stream=pdf_bytes,
            filetype="pdf",
        )

    except Exception as exc:
        raise PDFExtractionIntegrityError(
            "The PDF could not be opened for extraction."
        ) from exc

    try:
        with pdf:

            if pdf.is_encrypted:
                raise PDFExtractionIntegrityError(
                    "Encrypted PDFs cannot be extracted."
                )

            page_count = pdf.page_count

            if page_count <= 0:
                raise PDFExtractionIntegrityError(
                    "The PDF does not contain any pages."
                )

            if page_count > settings.max_pages:
                raise PDFExtractionIntegrityError(
                    f"The PDF exceeds the configured page limit "
                    f"of {settings.max_pages}."
                )

            extracted_pages = []

            for index in range(page_count):

                page = pdf.load_page(index)

                page_result = extract_page(
                    page=page,
                    page_number=index + 1,
                )

                extracted_pages.append(page_result)

    except PDFExtractionError:
        raise

    except Exception as exc:
        raise PDFExtractionIntegrityError(
            "An unexpected error occurred during PDF extraction."
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
        not page.is_empty
        for page in extracted_pages
    )

    empty_pages = [
        page.page_number
        for page in extracted_pages
        if page.is_empty
    ]

    quality_status, document_warnings = (
        determine_document_quality(extracted_pages)
    )

    return PDFExtractionResult(
        document_id=str(document_uuid),
        page_count=page_count,
        total_characters=total_characters,
        total_words=total_words,
        pages_with_text=pages_with_text,
        empty_pages=empty_pages,
        quality_status=quality_status,
        warnings=document_warnings,
        pages=extracted_pages,
    )


def serialize_extraction_result(
    result: PDFExtractionResult,
) -> dict:
    """Convert extraction results into JSON-compatible data."""

    return asdict(result)


def save_extraction_artifact(
    result: PDFExtractionResult,
    settings: DocumentSettings,
) -> Path:
    """
    Save the extraction result as a JSON artifact.

    The artifact is written atomically to the processed directory.
    """

    try:
        document_uuid = UUID(result.document_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise PDFExtractionStorageError(
            "Invalid document ID for extraction artifact."
        ) from exc

    processed_directory = (
        Path(settings.storage_root) / "processed"
    )

    try:
        processed_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            processed_directory / f"{document_uuid}.json"
        )

        payload = serialize_extraction_result(result)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix=f"{document_uuid}_",
            dir=processed_directory,
            delete=False,
        ) as temporary_file:

            temporary_path = Path(temporary_file.name)

            json.dump(
                payload,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )

            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(
            temporary_path,
            destination,
        )

        return destination

    except Exception as exc:

        if "temporary_path" in locals():
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise PDFExtractionStorageError(
            "Failed to save the PDF extraction artifact."
        ) from exc


def process_stored_pdf(
    pdf_path: Path,
    document_id: str,
    settings: DocumentSettings,
) -> tuple[PDFExtractionResult, Path]:
    """
    Complete Phase 7.3 processing for one stored PDF.

    1. Extract text.
    2. Normalize text.
    3. Analyze extraction quality.
    4. Save the JSON artifact.
    """

    result = extract_pdf_text(
        pdf_path=pdf_path,
        document_id=document_id,
        settings=settings,
    )

    artifact_path = save_extraction_artifact(
        result=result,
        settings=settings,
    )

    return result, artifact_path