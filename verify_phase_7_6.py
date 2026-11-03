from pathlib import Path
from uuid import uuid4
import json

from app.core.ocr_config import OCRSettings
from app.services.ocr_service import extract_pdf_with_ocr
from app.services.document_structure_service import (
    process_document_structure,
)


# Existing scanned PDF
PDF_PATH = Path("storage/documents/scanned_test.pdf")

# Storage configuration
STORAGE_ROOT = Path("storage")

# Generate a unique document ID
DOCUMENT_ID = str(uuid4())


def main():
    if not PDF_PATH.is_file():
        raise FileNotFoundError(
            f"PDF not found: {PDF_PATH.resolve()}"
        )

    print("\nPhase 7.6 real-PDF verification started.")
    print(f"PDF: {PDF_PATH}")

    # OCR configuration
    ocr_settings = OCRSettings(
        tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        language="eng",
        dpi=300,
        timeout_seconds=60,
        minimum_confidence=40,
        force_ocr=False,
    )

    # STEP 1: Extract OCR results
    print("\nRunning OCR processing...")

    ocr_result = extract_pdf_with_ocr(
        pdf_path=PDF_PATH,
        document_id=DOCUMENT_ID,
        settings=ocr_settings,
        max_pages=100,
    )

    print("\nOCR completed.")
    print(f"Pages: {ocr_result.page_count}")
    print(f"Pages with text: {ocr_result.pages_with_text}")
    print(f"Total words: {ocr_result.total_words}")
    print(f"OCR page results: {len(ocr_result.pages)}")

    # STEP 2: Extract document structure using existing OCR results
    print("\nExtracting document structure...")

    structure, structure_artifact_path = (
        process_document_structure(
            pdf_path=PDF_PATH,
            document_id=DOCUMENT_ID,
            storage_root=STORAGE_ROOT,
            ocr_pages=ocr_result.pages,
        )
    )

    print("\nStructure extraction completed.")

    # STEP 3: Validate structure
    assert structure is not None
    assert structure["document_id"] == DOCUMENT_ID
    assert Path(structure_artifact_path).is_file()

    print("\nStructure summary:")
    print(f"Sections: {len(structure.get('sections', []))}")
    print(f"Lists: {len(structure.get('lists', []))}")
    print(f"Tables: {len(structure.get('tables', []))}")
    print(f"Pages: {len(structure.get('pages', []))}")

    # STEP 4: Verify saved JSON artifact
    with open(
        structure_artifact_path,
        "r",
        encoding="utf-8",
    ) as file:
        saved_structure = json.load(file)

    assert saved_structure["document_id"] == DOCUMENT_ID

    print("\nStructure artifact verified.")
    print(f"Artifact location: {structure_artifact_path}")

    print("\n======================================")
    print("PHASE 7.6 REAL-PDF VERIFICATION PASSED")
    print("======================================")


if __name__ == "__main__":
    main()