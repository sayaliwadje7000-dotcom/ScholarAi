from pathlib import Path
from uuid import uuid4
from app.core.document_config import document_settings

from app.core.ocr_config import ocr_settings
from app.services.ocr_service import process_pdf_ocr

pdf_path = Path("storage/documents/scanned_test.pdf")

if not pdf_path.is_file():
    raise FileNotFoundError(f"PDF not found: {pdf_path.resolve()}")

document_id = str(uuid4())

print("Starting OCR...")

result, artifact_path = process_pdf_ocr(
    pdf_path=pdf_path,
    document_id=document_id,
    settings=ocr_settings,
    storage_root=document_settings.storage_root,
)

print("\nOCR COMPLETED")
print("Pages:", result.page_count)
print("Words:", result.total_words)
print("Quality:", result.quality_status)
print("Artifact:", artifact_path)