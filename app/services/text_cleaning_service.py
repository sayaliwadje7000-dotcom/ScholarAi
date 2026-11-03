import json
import re
import tempfile
import unicodedata

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


from app.core.text_cleaning_config import (
    TextCleaningSettings,
)


# ==========================================================
# EXCEPTIONS
# ==========================================================

class TextCleaningError(Exception):
    """Base exception for text cleaning."""


class TextCleaningInputError(TextCleaningError):
    """Raised when text cleaning input is invalid."""


class TextCleaningStorageError(TextCleaningError):
    """Raised when cleaned text cannot be stored."""


# ==========================================================
# UNICODE LIGATURES
# ==========================================================

LIGATURE_MAP = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "st",
    "\ufb06": "st",
}


# ==========================================================
# DATA MODELS
# ==========================================================

@dataclass(frozen=True)
class CleanedPageResult:

    page_number: int

    text: str

    original_character_count: int

    cleaned_character_count: int

    original_word_count: int

    cleaned_word_count: int

    changes_made: int

    warnings: list[str]


@dataclass(frozen=True)
class TextCleaningResult:

    document_id: str

    page_count: int

    total_original_characters: int

    total_cleaned_characters: int

    total_original_words: int

    total_cleaned_words: int

    total_changes: int

    quality_status: str

    warnings: list[str]

    pages: list[CleanedPageResult]


# ==========================================================
# BASIC HELPERS
# ==========================================================

def count_words(text: str) -> int:

    if not text.strip():

        return 0

    return len(text.split())


def normalize_line_endings(text: str) -> str:

    text = text.replace("\r\n", "\n")

    text = text.replace("\r", "\n")

    return text


# ==========================================================
# UNICODE NORMALIZATION
# ==========================================================

def normalize_unicode(
    text: str,
) -> str:

    if not isinstance(text, str):

        raise TextCleaningInputError(
            "Text must be a string."
        )

    return unicodedata.normalize(
        "NFC",
        text,
    )


def normalize_ligatures(
    text: str,
) -> str:

    for original, replacement in LIGATURE_MAP.items():

        text = text.replace(
            original,
            replacement,
        )

    return text


# ==========================================================
# CONTROL CHARACTER CLEANING
# ==========================================================

def remove_control_characters(
    text: str,
) -> str:

    cleaned = []

    for character in text:

        if character in ("\n", "\t"):

            cleaned.append(character)

            continue

        category = unicodedata.category(
            character
        )

        if category in ("Cc", "Cf"):

            continue

        cleaned.append(character)

    return "".join(cleaned)


# ==========================================================
# OCR ARTIFACT CLEANING
# ==========================================================

def clean_ocr_artifacts(
    text: str,
) -> str:

    # Remove null characters.
    text = text.replace(
        "\x00",
        "",
    )

    # Remove replacement characters.
    text = text.replace(
        "\ufffd",
        "",
    )

    # Normalize unusual spaces.
    text = text.replace(
        "\u00a0",
        " ",
    )

    text = text.replace(
        "\u2007",
        " ",
    )

    text = text.replace(
        "\u202f",
        " ",
    )

    # Remove soft hyphens.
    text = text.replace(
        "\u00ad",
        "",
    )

    return text


# ==========================================================
# WHITESPACE NORMALIZATION
# ==========================================================

def normalize_whitespace(
    text: str,
    settings: TextCleaningSettings,
) -> str:

    lines = text.split("\n")

    cleaned_lines = []

    blank_line_count = 0

    for line in lines:

        line = line.strip()

        line = re.sub(
            r"[ \t]+",
            " ",
            line,
        )

        if not line:

            blank_line_count += 1

            if (
                blank_line_count
                <= settings.maximum_consecutive_blank_lines
            ):

                cleaned_lines.append("")

            continue

        blank_line_count = 0

        cleaned_lines.append(line)

    return "\n".join(
        cleaned_lines
    ).strip()


# ==========================================================
# HYPHENATION REPAIR
# ==========================================================

def repair_hyphenated_words(
    text: str,
) -> str:

    """
    Join alphabetic words split across lines.

    Example:

        algo-
        rithm

    Becomes:

        algorithm

    Hyphens between numbers and mathematical
    expressions are not modified.
    """

    pattern = re.compile(
        r"(?<=[A-Za-z])-\n(?=[a-z])"
    )

    return pattern.sub(
        "",
        text,
    )


# ==========================================================
# REPEATED HEADER / FOOTER DETECTION
# ==========================================================

def normalize_comparison_line(
    line: str,
) -> str:

    line = line.strip().lower()

    line = re.sub(
        r"\s+",
        " ",
        line,
    )

    return line


def detect_repeated_lines(
    pages: list[Any],
    minimum_ratio: float,
) -> set[str]:

    if not pages:

        return set()

    line_counts = Counter()

    page_count = len(pages)

    for page in pages:

        text = getattr(
            page,
            "text",
            "",
        )

        lines = text.split("\n")

        page_lines = set()

        for line in lines:

            normalized = normalize_comparison_line(
                line
            )

            if len(normalized) < 3:

                continue

            page_lines.add(normalized)

        line_counts.update(
            page_lines
        )

    threshold = max(
        2,
        int(page_count * minimum_ratio),
    )

    return {
        line
        for line, count in line_counts.items()
        if count >= threshold
    }


# ==========================================================
# MAIN TEXT CLEANING FUNCTION
# ==========================================================

def clean_text(
    text: str,
    settings: TextCleaningSettings | None = None,
) -> tuple[str, int]:

    settings = (
        settings
        or TextCleaningSettings()
    )

    if not isinstance(text, str):

        raise TextCleaningInputError(
            "Input text must be a string."
        )

    original_text = text

    text = normalize_line_endings(
        text
    )

    if settings.normalize_unicode:

        text = normalize_unicode(
            text
        )

    if settings.normalize_ligatures:

        text = normalize_ligatures(
            text
        )

    text = clean_ocr_artifacts(
        text
    )

    if settings.remove_control_characters:

        text = remove_control_characters(
            text
        )

    if settings.repair_hyphenated_words:

        text = repair_hyphenated_words(
            text
        )

    if settings.normalize_whitespace:

        text = normalize_whitespace(
            text,
            settings,
        )

    changes = sum(
        1
        for old, new in zip(
            original_text,
            text,
        )
        if old != new
    )

    changes += abs(
        len(original_text) - len(text)
    )

    return text, changes


# ==========================================================
# PAGE CLEANING
# ==========================================================

def clean_document_pages(
    pages: list[Any],
    settings: TextCleaningSettings | None = None,
) -> list[CleanedPageResult]:

    settings = (
        settings
        or TextCleaningSettings()
    )

    if not isinstance(pages, list):

        raise TextCleaningInputError(
            "Pages must be provided as a list."
        )

    repeated_lines = detect_repeated_lines(
        pages,
        settings.minimum_repeated_page_ratio,
    )

    results = []

    for page in pages:

        page_number = getattr(
            page,
            "page_number",
            None,
        )

        original_text = getattr(
            page,
            "text",
            None,
        )

        if not isinstance(
            original_text,
            str,
        ):

            raise TextCleaningInputError(
                "Every page must contain string text."
            )

        original_characters = len(
            original_text
        )

        original_words = count_words(
            original_text
        )

        cleaned_text, changes = clean_text(
            original_text,
            settings,
        )

        warnings = []

        if not cleaned_text:

            warnings.append(
                "No readable text remains after cleaning."
            )

        if (
            settings.remove_repeated_headers
            or settings.remove_repeated_footers
        ):

            lines = cleaned_text.split("\n")

            filtered_lines = []

            for index, line in enumerate(lines):

                normalized = normalize_comparison_line(
                    line
                )

                is_first_line = index == 0

                is_last_line = (
                    index == len(lines) - 1
                )

                should_remove = False

                if (
                    settings.remove_repeated_headers
                    and is_first_line
                    and normalized in repeated_lines
                ):

                    should_remove = True

                if (
                    settings.remove_repeated_footers
                    and is_last_line
                    and normalized in repeated_lines
                ):

                    should_remove = True

                if not should_remove:

                    filtered_lines.append(
                        line
                    )

            cleaned_text = "\n".join(
                filtered_lines
            ).strip()

        results.append(
            CleanedPageResult(
                page_number=page_number,
                text=cleaned_text,
                original_character_count=original_characters,
                cleaned_character_count=len(
                    cleaned_text
                ),
                original_word_count=original_words,
                cleaned_word_count=count_words(
                    cleaned_text
                ),
                changes_made=changes,
                warnings=warnings,
            )
        )

    return results


# ==========================================================
# DOCUMENT QUALITY ANALYSIS
# ==========================================================

def determine_cleaning_quality(
    pages: list[CleanedPageResult],
) -> tuple[str, list[str]]:

    warnings = []

    empty_pages = [
        page.page_number
        for page in pages
        if not page.text.strip()
    ]

    if not pages:

        return (
            "empty",
            ["No pages were provided."],
        )

    if len(empty_pages) == len(pages):

        return (
            "poor",
            ["No readable text remains."],
        )

    if empty_pages:

        warnings.append(
            f"Empty pages after cleaning: {empty_pages}"
        )

        return (
            "partial",
            warnings,
        )

    for page in pages:

        for warning in page.warnings:

            warnings.append(
                f"Page {page.page_number}: {warning}"
            )

    if warnings:

        return (
            "partial",
            warnings,
        )

    return (
        "good",
        warnings,
    )


# ==========================================================
# DOCUMENT CLEANING PIPELINE
# ==========================================================

def clean_document_text(
    document_id: str,
    pages: list[Any],
    settings: TextCleaningSettings | None = None,
) -> TextCleaningResult:

    if not document_id:

        raise TextCleaningInputError(
            "Document ID is required."
        )

    settings = (
        settings
        or TextCleaningSettings()
    )

    cleaned_pages = clean_document_pages(
        pages,
        settings,
    )

    quality_status, warnings = (
        determine_cleaning_quality(
            cleaned_pages
        )
    )

    return TextCleaningResult(
        document_id=str(document_id),
        page_count=len(cleaned_pages),
        total_original_characters=sum(
            page.original_character_count
            for page in cleaned_pages
        ),
        total_cleaned_characters=sum(
            page.cleaned_character_count
            for page in cleaned_pages
        ),
        total_original_words=sum(
            page.original_word_count
            for page in cleaned_pages
        ),
        total_cleaned_words=sum(
            page.cleaned_word_count
            for page in cleaned_pages
        ),
        total_changes=sum(
            page.changes_made
            for page in cleaned_pages
        ),
        quality_status=quality_status,
        warnings=warnings,
        pages=cleaned_pages,
    )


# ==========================================================
# JSON ARTIFACT STORAGE
# ==========================================================

def save_cleaned_text_artifact(
    result: TextCleaningResult,
    storage_root: Path,
) -> Path:

    storage_root = Path(
        storage_root
    )

    processed_directory = (
        storage_root / "processed"
    )

    processed_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact_path = (
        processed_directory
        / f"{result.document_id}_cleaned.json"
    )

    artifact = asdict(
        result
    )

    temporary_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            dir=processed_directory,
            delete=False,
        ) as temporary_file:

            json.dump(
                artifact,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )

            temporary_path = Path(
                temporary_file.name
            )

        temporary_path.replace(
            artifact_path
        )

        return artifact_path

    except Exception as exc:

        if (
            temporary_path
            and temporary_path.exists()
        ):

            temporary_path.unlink(
                missing_ok=True
            )

        raise TextCleaningStorageError(
            "Unable to save cleaned text artifact."
        ) from exc