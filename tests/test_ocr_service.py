import json

from dataclasses import replace
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import pymupdf
import pytest

from app.core.ocr_config import OCRSettings

from app.services.ocr_service import (
    OCRPageResult,
    OCRDocumentResult,
    OCRConfigurationError,
    OCRProcessingError,
    OCRStorageError,
    calculate_page_word_count,
    determine_ocr_document_quality,
    extract_text_with_ocr,
    process_pdf_page,
    render_pdf_page,
    save_ocr_artifact,
)


@pytest.fixture
def ocr_settings():

    return OCRSettings(
        tesseract_cmd="tesseract.exe",
        language="eng",
        dpi=300,
        timeout_seconds=60,
        minimum_confidence=40,
        force_ocr=False,
    )


@pytest.fixture
def sample_pdf_page():

    pdf = pymupdf.open()

    page = pdf.new_page()

    page.insert_text(
        (72, 72),
        "ScholarAI native text extraction.",
    )

    yield page

    pdf.close()


def test_calculate_page_word_count():

    assert calculate_page_word_count(
        "ScholarAI helps students learn."
    ) == 4


def test_calculate_page_word_count_empty():

    assert calculate_page_word_count("") == 0


def test_render_pdf_page(
    sample_pdf_page,
    ocr_settings,
):

    image = render_pdf_page(
        sample_pdf_page,
        ocr_settings.dpi,
    )

    assert image.width > 0
    assert image.height > 0
    assert image.mode == "RGB"

    image.close()


def test_native_text_does_not_require_ocr(
    sample_pdf_page,
    ocr_settings,
):

    result = process_pdf_page(
        sample_pdf_page,
        1,
        ocr_settings,
    )

    assert result.extraction_method == "native"
    assert result.ocr_status == "not_required"

    assert "ScholarAI" in result.text

    assert result.average_confidence is None


def test_native_text_can_be_force_ocr(
    sample_pdf_page,
    ocr_settings,
):

    settings = replace(
        ocr_settings,
        force_ocr=True,
    )

    with patch(
        "app.services.ocr_service.extract_text_with_ocr",
        return_value=("OCR extracted content.", 92.5),
    ):

        result = process_pdf_page(
            sample_pdf_page,
            1,
            settings,
        )

    assert result.extraction_method == "ocr"
    assert result.ocr_status == "completed"

    assert result.text == "OCR extracted content."

    assert result.average_confidence == 92.5


def test_ocr_text_extraction(
    ocr_settings,
):

    fake_data = {
        "text": [
            "ScholarAI",
            "helps",
            "students",
        ],
        "conf": [
            "95",
            "92",
            "90",
        ],
    }

    with patch(
        "app.services.ocr_service.pytesseract.image_to_data",
        return_value=fake_data,
    ):

        from PIL import Image

        image = Image.new(
            "RGB",
            (100, 100),
        )

        text, confidence = extract_text_with_ocr(
            image,
            ocr_settings,
        )

        image.close()

    assert text == "ScholarAI helps students"
    assert confidence == 92.33


def test_ocr_ignores_invalid_confidence(
    ocr_settings,
):

    fake_data = {
        "text": [
            "ScholarAI",
            "invalid",
        ],
        "conf": [
            "90",
            "-1",
        ],
    }

    with patch(
        "app.services.ocr_service.pytesseract.image_to_data",
        return_value=fake_data,
    ):

        from PIL import Image

        image = Image.new(
            "RGB",
            (100, 100),
        )

        text, confidence = extract_text_with_ocr(
            image,
            ocr_settings,
        )

        image.close()

    assert text == "ScholarAI"
    assert confidence == 90.0


def test_ocr_no_text(
    ocr_settings,
):

    fake_data = {
        "text": ["", " "],
        "conf": ["-1", "-1"],
    }

    with patch(
        "app.services.ocr_service.pytesseract.image_to_data",
        return_value=fake_data,
    ):

        from PIL import Image

        image = Image.new(
            "RGB",
            (100, 100),
        )

        text, confidence = extract_text_with_ocr(
            image,
            ocr_settings,
        )

        image.close()

    assert text == ""
    assert confidence is None


def test_ocr_confidence_threshold(
    sample_pdf_page,
    ocr_settings,
):

    with patch(
        "app.services.ocr_service.extract_text_with_ocr",
        return_value=("Recognized text.", 25.0),
    ):

        settings = replace(
            ocr_settings,
            force_ocr=True,
        )

        result = process_pdf_page(
            sample_pdf_page,
            1,
            settings,
        )

    assert result.low_confidence is True
    assert result.warnings


def test_high_confidence_ocr(
    sample_pdf_page,
    ocr_settings,
):

    with patch(
        "app.services.ocr_service.extract_text_with_ocr",
        return_value=("Recognized text.", 95.0),
    ):

        settings = replace(
            ocr_settings,
            force_ocr=True,
        )

        result = process_pdf_page(
            sample_pdf_page,
            1,
            settings,
        )

    assert result.low_confidence is False
    assert result.ocr_status == "completed"


def test_quality_good():

    pages = [
        OCRPageResult(
            page_number=1,
            text="Native text.",
            extraction_method="native",
            ocr_status="not_required",
            character_count=12,
            word_count=2,
            average_confidence=None,
            low_confidence=False,
            warnings=[],
        ),
    ]

    status, ocr_pages, failed_pages, warnings = (
        determine_ocr_document_quality(pages)
    )

    assert status == "good"
    assert ocr_pages == []
    assert failed_pages == []
    assert warnings == []


def test_quality_partial():

    pages = [
        OCRPageResult(
            page_number=1,
            text="Readable text.",
            extraction_method="native",
            ocr_status="not_required",
            character_count=14,
            word_count=2,
            average_confidence=None,
            low_confidence=False,
            warnings=[],
        ),
        OCRPageResult(
            page_number=2,
            text="",
            extraction_method="ocr",
            ocr_status="no_text",
            character_count=0,
            word_count=0,
            average_confidence=None,
            low_confidence=True,
            warnings=["No text found."],
        ),
    ]

    status, ocr_pages, failed_pages, warnings = (
        determine_ocr_document_quality(pages)
    )

    assert status == "partial"
    assert ocr_pages == [2]
    assert failed_pages == []
    assert warnings


def test_quality_ocr_failed():

    pages = [
        OCRPageResult(
            page_number=1,
            text="",
            extraction_method="ocr",
            ocr_status="failed",
            character_count=0,
            word_count=0,
            average_confidence=None,
            low_confidence=True,
            warnings=["OCR failed."],
        ),
    ]

    status, ocr_pages, failed_pages, warnings = (
        determine_ocr_document_quality(pages)
    )

    assert status == "ocr_failed"
    assert ocr_pages == [1]
    assert failed_pages == [1]


def test_quality_needs_ocr():

    pages = [
        OCRPageResult(
            page_number=1,
            text="",
            extraction_method="ocr",
            ocr_status="no_text",
            character_count=0,
            word_count=0,
            average_confidence=None,
            low_confidence=True,
            warnings=["No text found."],
        ),
    ]

    status, _, _, _ = determine_ocr_document_quality(pages)

    assert status == "needs_ocr"


def test_save_ocr_artifact(tmp_path):

    document_id = str(uuid4())

    result = OCRDocumentResult(
    document_id=document_id,
    page_count=1,
    pages_with_text=1,
    total_characters=14,
    total_words=2,
    average_ocr_confidence=92.5,
    quality_status="good",
    ocr_pages=[1],
    failed_pages=[],
    warnings=[],
    pages=[],
)
        
    ()

    artifact_path = save_ocr_artifact(
        result,
        tmp_path,
    )

    assert artifact_path.exists()

    data = json.loads(
        artifact_path.read_text(
            encoding="utf-8"
        )
    )

    assert data["document_id"] == document_id
    assert data["quality_status"] == "good"
    assert data["average_ocr_confidence"] == 92.5


def test_artifact_filename(tmp_path):

    document_id = str(uuid4())

    result = OCRDocumentResult(
    document_id=document_id,
    page_count=0,
    pages_with_text=0,
    total_characters=0,
    total_words=0,
    average_ocr_confidence=None,
    quality_status="needs_ocr",
    ocr_pages=[],
    failed_pages=[],
    warnings=[],
    pages=[],
)
        
    ()

    artifact = save_ocr_artifact(
        result,
        tmp_path,
    )

    assert artifact.name == f"{document_id}_ocr.json"


def test_invalid_document_uuid(tmp_path):

    result = type(
        "TestResult",
        (),
        {
            "document_id": "invalid",
        },
    )()

    with pytest.raises(OCRStorageError):

        save_ocr_artifact(
            result,
            tmp_path,
        )