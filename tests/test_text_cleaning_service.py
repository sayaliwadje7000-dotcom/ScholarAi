import json

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.core.text_cleaning_config import (
    TextCleaningSettings,
)

from app.services.text_cleaning_service import (
    clean_text,
    normalize_unicode,
    normalize_ligatures,
    remove_control_characters,
    clean_ocr_artifacts,
    normalize_whitespace,
    repair_hyphenated_words,
    clean_document_pages,
    clean_document_text,
    determine_cleaning_quality,
    save_cleaned_text_artifact,
    TextCleaningInputError,
)


@dataclass
class MockPage:

    page_number: int

    text: str


# ==========================================================
# UNICODE TESTS
# ==========================================================

def test_unicode_normalization():

    result = normalize_unicode(
        "cafe\u0301"
    )

    assert result == "café"


def test_ligature_normalization():

    result = normalize_ligatures(
        "ﬁle ﬂow ﬀ"
    )

    assert result == "file flow ff"


# ==========================================================
# CONTROL CHARACTER TESTS
# ==========================================================

def test_remove_control_characters():

    result = remove_control_characters(
        "Hello\x01World"
    )

    assert result == "HelloWorld"


def test_preserve_newlines():

    result = remove_control_characters(
        "Hello\nWorld"
    )

    assert result == "Hello\nWorld"


# ==========================================================
# OCR ARTIFACT TESTS
# ==========================================================

def test_clean_ocr_artifacts():

    result = clean_ocr_artifacts(
        "Hello\u00a0World\ufffd"
    )

    assert result == "Hello World"


def test_remove_soft_hyphen():

    result = clean_ocr_artifacts(
        "algo\u00ad rithm"
    )

    assert result == "algo rithm"


# ==========================================================
# WHITESPACE TESTS
# ==========================================================

def test_normalize_whitespace():

    settings = TextCleaningSettings()

    result = normalize_whitespace(
        "  Hello     World  \n\n\n  Python  ",
        settings,
    )

    assert result == "Hello World\n\nPython"


def test_preserve_paragraph_break():

    settings = TextCleaningSettings()

    result = normalize_whitespace(
        "First paragraph.\n\nSecond paragraph.",
        settings,
    )

    assert result == (
        "First paragraph.\n\nSecond paragraph."
    )


# ==========================================================
# HYPHENATION TESTS
# ==========================================================

def test_repair_hyphenated_word():

    result = repair_hyphenated_words(
        "algo-\nrithm"
    )

    assert result == "algorithm"


def test_preserve_normal_hyphen():

    result = repair_hyphenated_words(
        "state-of-the-art"
    )

    assert result == "state-of-the-art"


def test_preserve_numeric_expression():

    result = repair_hyphenated_words(
        "10-\n20"
    )

    assert result == "10-\n20"


# ==========================================================
# MAIN CLEANING TESTS
# ==========================================================

def test_clean_text_combines_all_operations():

    text = (
        "  ﬁle   processing  \n"
        "algo-\nrithm\x00"
    )

    cleaned, changes = clean_text(
        text
    )

    assert cleaned == (
        "file processing\nalgorithm"
    )

    assert changes > 0


def test_clean_text_rejects_non_string():

    with pytest.raises(
        TextCleaningInputError
    ):

        clean_text(123)


def test_clean_empty_text():

    cleaned, changes = clean_text(
        ""
    )

    assert cleaned == ""

    assert changes == 0


# ==========================================================
# PAGE CLEANING TESTS
# ==========================================================

def test_clean_document_pages():

    pages = [
        MockPage(
            page_number=1,
            text="Hello   World",
        ),
        MockPage(
            page_number=2,
            text="Python   Programming",
        ),
    ]

    results = clean_document_pages(
        pages
    )

    assert len(results) == 2

    assert results[0].text == "Hello World"

    assert results[1].text == "Python Programming"


def test_clean_document_pages_preserves_page_numbers():

    pages = [
        MockPage(
            page_number=4,
            text="Page four",
        ),
    ]

    results = clean_document_pages(
        pages
    )

    assert results[0].page_number == 4


def test_clean_document_pages_rejects_invalid_pages():

    with pytest.raises(
        TextCleaningInputError
    ):

        clean_document_pages(
            "invalid"
        )


# ==========================================================
# DOCUMENT PIPELINE TESTS
# ==========================================================

def test_clean_document_text():

    pages = [
        MockPage(
            page_number=1,
            text="Hello   World",
        ),
        MockPage(
            page_number=2,
            text="Python   Programming",
        ),
    ]

    result = clean_document_text(
        document_id="document-123",
        pages=pages,
    )

    assert result.document_id == "document-123"

    assert result.page_count == 2

    assert result.total_cleaned_words == 4

    assert result.quality_status == "good"


def test_clean_document_text_rejects_missing_id():

    with pytest.raises(
        TextCleaningInputError
    ):

        clean_document_text(
            document_id="",
            pages=[],
        )


def test_empty_document_quality():

    status, warnings = determine_cleaning_quality(
        []
    )

    assert status == "empty"

    assert warnings


# ==========================================================
# ARTIFACT STORAGE TESTS
# ==========================================================

def test_save_cleaned_text_artifact(
    tmp_path: Path,
):

    pages = [
        MockPage(
            page_number=1,
            text="Hello   World",
        ),
    ]

    result = clean_document_text(
        document_id="document-123",
        pages=pages,
    )

    artifact_path = save_cleaned_text_artifact(
        result,
        tmp_path,
    )

    assert artifact_path.is_file()

    with open(
        artifact_path,
        "r",
        encoding="utf-8",
    ) as file:

        artifact = json.load(file)

    assert artifact["document_id"] == "document-123"

    assert artifact["pages"][0]["text"] == "Hello World"


def test_artifact_contains_cleaning_metadata(
    tmp_path: Path,
):

    pages = [
        MockPage(
            page_number=1,
            text="Hello   World",
        ),
    ]

    result = clean_document_text(
        document_id="document-456",
        pages=pages,
    )

    artifact_path = save_cleaned_text_artifact(
        result,
        tmp_path,
    )

    with open(
        artifact_path,
        "r",
        encoding="utf-8",
    ) as file:

        artifact = json.load(file)

    assert "total_changes" in artifact

    assert "quality_status" in artifact

    assert "total_cleaned_words" in artifact