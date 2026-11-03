import json

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pymupdf
import pytest

from app.core.document_config import load_document_settings

from app.services.pdf_extraction_service import (
    PDFExtractionError,
    PDFExtractionIntegrityError,
    PDFExtractionStorageError,
    normalize_extracted_text,
    calculate_word_count,
    determine_document_quality,
    extract_pdf_text,
    save_extraction_artifact,
    process_stored_pdf,
)


@pytest.fixture
def document_settings_fixture(tmp_path):

    settings = replace(
        load_document_settings(),
        storage_root=tmp_path,
        max_pages=10,
        create_storage_directories=True,
    )

    return settings


def create_test_pdf(
    path: Path,
    page_texts: list[str],
):
    """Create a test PDF with the supplied page text."""

    pdf = pymupdf.open()

    for text in page_texts:

        page = pdf.new_page()

        if text:
            page.insert_text(
                (72, 72),
                text,
                fontsize=12,
            )

    pdf.save(path)
    pdf.close()

    return path


def test_normalize_extracted_text():

    raw_text = (
        "  ScholarAI   Project  \r\n"
        "Data\tStructures\x00"
    )

    result = normalize_extracted_text(raw_text)

    assert result == (
        "ScholarAI Project\n"
        "Data Structures"
    )


def test_normalize_unicode():

    raw_text = "Cafe\u0301"

    result = normalize_extracted_text(raw_text)

    assert result == "Café"


def test_normalize_empty_text():

    assert normalize_extracted_text("") == ""


def test_calculate_word_count():

    assert calculate_word_count(
        "ScholarAI helps students learn better."
    ) == 5


def test_calculate_word_count_empty():

    assert calculate_word_count("") == 0


def test_extract_single_page_pdf(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "single.pdf",
        ["ScholarAI PDF extraction test."],
    )

    document_id = str(uuid4())

    result = extract_pdf_text(
        pdf_path,
        document_id,
        document_settings_fixture,
    )

    assert result.page_count == 1
    assert result.pages_with_text == 1
    assert result.empty_pages == []
    assert result.quality_status == "good"

    assert "ScholarAI PDF extraction test." in (
        result.pages[0].text
    )


def test_extract_multiple_pages(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "multiple.pdf",
        [
            "First page content.",
            "Second page content.",
            "Third page content.",
        ],
    )

    result = extract_pdf_text(
        pdf_path,
        str(uuid4()),
        document_settings_fixture,
    )

    assert result.page_count == 3
    assert result.pages_with_text == 3
    assert len(result.pages) == 3

    assert result.pages[0].page_number == 1
    assert result.pages[1].page_number == 2
    assert result.pages[2].page_number == 3

    assert "First page content." in result.pages[0].text
    assert "Second page content." in result.pages[1].text
    assert "Third page content." in result.pages[2].text


def test_page_metadata_is_extracted(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "metadata.pdf",
        ["Metadata test."],
    )

    result = extract_pdf_text(
        pdf_path,
        str(uuid4()),
        document_settings_fixture,
    )

    page = result.pages[0]

    assert page.page_number == 1
    assert page.width > 0
    assert page.height > 0
    assert page.rotation == 0
    assert page.character_count > 0
    assert page.word_count > 0
    assert page.is_empty is False


def test_detect_empty_page(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "empty_page.pdf",
        [
            "Page with content.",
            "",
        ],
    )

    result = extract_pdf_text(
        pdf_path,
        str(uuid4()),
        document_settings_fixture,
    )

    assert result.page_count == 2
    assert result.pages_with_text == 1
    assert result.empty_pages == [2]
    assert result.quality_status == "partial"


def test_detect_document_needing_ocr(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "scanned_like.pdf",
        [
            "",
            "",
        ],
    )

    result = extract_pdf_text(
        pdf_path,
        str(uuid4()),
        document_settings_fixture,
    )

    assert result.pages_with_text == 0
    assert result.empty_pages == [1, 2]
    assert result.quality_status == "needs_ocr"

    assert any(
        "OCR" in warning
        for warning in result.warnings
    )


def test_reject_missing_pdf(
    tmp_path,
    document_settings_fixture,
):

    with pytest.raises(PDFExtractionError):
        extract_pdf_text(
            tmp_path / "missing.pdf",
            str(uuid4()),
            document_settings_fixture,
        )


def test_reject_empty_file(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"")

    with pytest.raises(PDFExtractionIntegrityError):
        extract_pdf_text(
            pdf_path,
            str(uuid4()),
            document_settings_fixture,
        )


def test_reject_invalid_pdf(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = tmp_path / "invalid.pdf"
    pdf_path.write_bytes(b"This is not a PDF.")

    with pytest.raises(PDFExtractionIntegrityError):
        extract_pdf_text(
            pdf_path,
            str(uuid4()),
            document_settings_fixture,
        )


def test_reject_invalid_document_uuid(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "valid.pdf",
        ["Valid PDF."],
    )

    with pytest.raises(PDFExtractionError):
        extract_pdf_text(
            pdf_path,
            "../invalid-id",
            document_settings_fixture,
        )


def test_reject_pdf_exceeding_page_limit(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "too_many_pages.pdf",
        [
            "Page 1",
            "Page 2",
            "Page 3",
        ],
    )

    settings = replace(
        document_settings_fixture,
        max_pages=2,
    )

    with pytest.raises(PDFExtractionIntegrityError):
        extract_pdf_text(
            pdf_path,
            str(uuid4()),
            settings,
        )


def test_save_extraction_artifact(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "artifact.pdf",
        ["Artifact generation test."],
    )

    document_id = str(uuid4())

    result = extract_pdf_text(
        pdf_path,
        document_id,
        document_settings_fixture,
    )

    artifact_path = save_extraction_artifact(
        result,
        document_settings_fixture,
    )

    assert artifact_path.exists()
    assert artifact_path.suffix == ".json"

    with artifact_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    assert data["document_id"] == document_id
    assert data["page_count"] == 1
    assert data["quality_status"] == "good"


def test_artifact_contains_page_text(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "content.pdf",
        ["Important study material."],
    )

    result = extract_pdf_text(
        pdf_path,
        str(uuid4()),
        document_settings_fixture,
    )

    artifact_path = save_extraction_artifact(
        result,
        document_settings_fixture,
    )

    data = json.loads(
        artifact_path.read_text(encoding="utf-8")
    )

    assert (
        "Important study material."
        in data["pages"][0]["text"]
    )


def test_process_stored_pdf_end_to_end(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "end_to_end.pdf",
        [
            "ScholarAI first page.",
            "ScholarAI second page.",
        ],
    )

    document_id = str(uuid4())

    result, artifact_path = process_stored_pdf(
        pdf_path,
        document_id,
        document_settings_fixture,
    )

    assert result.page_count == 2
    assert result.pages_with_text == 2
    assert result.quality_status == "good"

    assert artifact_path.exists()


def test_artifact_directory_is_created(
    tmp_path,
    document_settings_fixture,
):

    pdf_path = create_test_pdf(
        tmp_path / "directory.pdf",
        ["Directory creation test."],
    )

    result = extract_pdf_text(
        pdf_path,
        str(uuid4()),
        document_settings_fixture,
    )

    artifact_path = save_extraction_artifact(
        result,
        document_settings_fixture,
    )

    assert artifact_path.parent.exists()


def test_artifact_uses_document_uuid(
    tmp_path,
    document_settings_fixture,
):

    document_id = str(uuid4())

    pdf_path = create_test_pdf(
        tmp_path / "uuid.pdf",
        ["UUID test."],
    )

    result = extract_pdf_text(
        pdf_path,
        document_id,
        document_settings_fixture,
    )

    artifact_path = save_extraction_artifact(
        result,
        document_settings_fixture,
    )

    assert artifact_path.name == f"{document_id}.json"


def test_quality_analysis_good_pages():

    from app.services.pdf_extraction_service import (
        PageExtractionResult,
    )

    page = PageExtractionResult(
        page_number=1,
        text="This is readable text.",
        width=595,
        height=842,
        rotation=0,
        character_count=23,
        word_count=4,
        is_empty=False,
        warnings=[],
    )

    status, warnings = determine_document_quality([page])

    assert status == "good"
    assert warnings == []


def test_quality_analysis_empty_pages():

    from app.services.pdf_extraction_service import (
        PageExtractionResult,
    )

    page = PageExtractionResult(
        page_number=1,
        text="",
        width=595,
        height=842,
        rotation=0,
        character_count=0,
        word_count=0,
        is_empty=True,
        warnings=["No extractable text found on this page."],
    )

    status, warnings = determine_document_quality([page])

    assert status == "needs_ocr"
    assert warnings


def test_quality_analysis_partial_document():

    from app.services.pdf_extraction_service import (
        PageExtractionResult,
    )

    pages = [
        PageExtractionResult(
            page_number=1,
            text="Readable content.",
            width=595,
            height=842,
            rotation=0,
            character_count=17,
            word_count=2,
            is_empty=False,
            warnings=[],
        ),
        PageExtractionResult(
            page_number=2,
            text="",
            width=595,
            height=842,
            rotation=0,
            character_count=0,
            word_count=0,
            is_empty=True,
            warnings=["No extractable text found on this page."],
        ),
    ]

    status, warnings = determine_document_quality(pages)

    assert status == "partial"
    assert warnings