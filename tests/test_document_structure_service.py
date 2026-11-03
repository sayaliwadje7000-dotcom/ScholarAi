import json

from pathlib import Path
from uuid import uuid4

import pymupdf
import pytest

from app.services.document_structure_service import (
    DocumentStructureInputError,
    DocumentStructureStorageError,
    detect_heading,
    detect_list_item,
    extract_document_structure,
    process_document_structure,
    save_structure_artifact,
)


@pytest.fixture
def sample_pdf(tmp_path):

    path = tmp_path / "sample.pdf"

    doc = pymupdf.open()

    page = doc.new_page()

    page.insert_text(
        (72, 60),
        "UNIT 1: DATA STRUCTURES",
        fontsize=20,
        fontname="hebo",
    )

    page.insert_text(
        (72, 100),
        "1.1 Introduction",
        fontsize=15,
        fontname="hebo",
    )

    page.insert_text(
        (72, 130),
        "A data structure organizes data for efficient use.",
        fontsize=11,
    )

    page.insert_text(
        (72, 165),
        "Types of structures:",
        fontsize=11,
    )

    page.insert_text(
        (90, 190),
        "1. Linear structures",
        fontsize=11,
    )

    page.insert_text(
        (90, 210),
        "2. Non-linear structures",
        fontsize=11,
    )

    doc.save(path)

    doc.close()

    return path


def test_detect_numbered_heading():

    result = detect_heading(
        "1.2 Classification of Data Structures"
    )

    assert result is not None

    assert result["type"] == "heading"

    assert result["level"] == 2


def test_detect_unit_heading():

    result = detect_heading(
        "UNIT 2: TREES"
    )

    assert result is not None

    assert result["level"] == 1


def test_reject_normal_sentence():

    result = detect_heading(
        "This is a normal sentence."
    )

    assert result is None


def test_detect_bullet_list():

    result = detect_list_item(
        "• Arrays"
    )

    assert result["marker_type"] == "bullet"

    assert result["text"] == "Arrays"


def test_detect_numbered_list():

    result = detect_list_item(
        "2. Linked lists"
    )

    assert result["marker_type"] == "numbered"

    assert result["text"] == "Linked lists"


def test_extract_native_pdf_structure(sample_pdf):

    document_id = str(uuid4())

    result = extract_document_structure(
        pdf_path=sample_pdf,
        document_id=document_id,
    )

    assert result["document_id"] == document_id

    assert result["page_count"] == 1

    assert result["summary"]["heading_count"] >= 2

    assert result["summary"]["paragraph_count"] >= 1

    assert result["sections"][0]["heading"].startswith(
        "UNIT 1"
    )

    assert result["sections"][0]["subsections"][0][
        "heading"
    ].startswith("1.1")


def test_ocr_fallback(tmp_path):

    path = tmp_path / "scanned.pdf"

    doc = pymupdf.open()

    doc.new_page()

    doc.save(path)

    doc.close()

    result = extract_document_structure(
        pdf_path=path,
        document_id=str(uuid4()),
        ocr_pages=[
            {
                "page_number": 1,
                "text": (
                    "CHAPTER 1: INTRODUCTION\n"
                    "This is OCR extracted content."
                ),
            }
        ],
    )

    assert result["pages"][0]["source"] == "ocr_text"

    assert result["document_title"] == (
        "CHAPTER 1: INTRODUCTION"
    )


def test_empty_page_warning(tmp_path):

    path = tmp_path / "empty.pdf"

    doc = pymupdf.open()

    doc.new_page()

    doc.save(path)

    doc.close()

    result = extract_document_structure(
        pdf_path=path,
        document_id=str(uuid4()),
    )

    assert len(result["warnings"]) > 0


def test_missing_pdf(tmp_path):

    with pytest.raises(DocumentStructureInputError):

        extract_document_structure(
            pdf_path=tmp_path / "missing.pdf",
            document_id=str(uuid4()),
        )


def test_invalid_uuid(sample_pdf):

    with pytest.raises(DocumentStructureInputError):

        extract_document_structure(
            pdf_path=sample_pdf,
            document_id="invalid-id",
        )


def test_save_structure_artifact(tmp_path):

    document_id = str(uuid4())

    structure = {
        "document_id": document_id,
        "sections": [],
        "warnings": [],
    }

    artifact_path = save_structure_artifact(
        structure=structure,
        storage_root=tmp_path,
    )

    assert artifact_path.exists()

    assert artifact_path.name == (
        f"{document_id}_structure.json"
    )

    saved_data = json.loads(
        artifact_path.read_text(
            encoding="utf-8"
        )
    )

    assert saved_data["document_id"] == document_id


def test_complete_structure_processing(
    sample_pdf,
    tmp_path,
):

    document_id = str(uuid4())

    structure, artifact_path = process_document_structure(
        pdf_path=sample_pdf,
        document_id=document_id,
        storage_root=tmp_path,
    )

    assert artifact_path.exists()

    assert structure["document_id"] == document_id


def test_invalid_artifact_id(tmp_path):

    with pytest.raises(DocumentStructureStorageError):

        save_structure_artifact(
            structure={
                "document_id": "invalid-id"
            },
            storage_root=tmp_path,
        )