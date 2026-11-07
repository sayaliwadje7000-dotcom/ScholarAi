from pathlib import Path
from sqlalchemy import select, func
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

PDF_PATH = Path(
    r"C:\Users\Sayali\Downloads\NoT Notes-(Unit-I - II).docx.pdf"
)

from app.database.session import SessionLocal
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.chunk_embedding import ChunkEmbedding

from app.core.document_config import document_settings
from app.core.ocr_config import load_ocr_settings

from app.services.document_storage_service import (
    save_document,
    get_document_path,
)
from app.services.document_processing_service import process_document


def main():
    if not PDF_PATH.is_file():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    if PDF_PATH.suffix.lower() != ".pdf":
        raise ValueError("The supplied file is not a PDF.")

    print("\n=== SCHOLARAI PHASE 8 REAL-PDF VERIFICATION ===")
    print(f"File: {PDF_PATH.name}")
    print(f"Size: {PDF_PATH.stat().st_size:,} bytes")

    content = PDF_PATH.read_bytes()

    db = SessionLocal()
    stored = None

    try:
        user_id = db.execute(
            select(User.id).limit(1)
        ).scalar_one_or_none()

        if user_id is None:
            raise RuntimeError(
                "No user exists in the database. Create a test user first."
            )

        print("\n[1/5] Registering and storing PDF...")
        stored = save_document(
            content=content,
            original_filename=PDF_PATH.name,
            content_type="application/pdf",
            settings=document_settings,
        )

        document = Document(
            id=stored.document_id,
            user_id=user_id,
            original_filename=stored.original_filename,
            storage_key=stored.storage_key,
            mime_type=stored.mime_type,
            file_size_bytes=stored.file_size_bytes,
            checksum_sha256=stored.checksum_sha256,
            page_count=stored.page_count,
            processing_status="pending",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        print(f"Document ID: {document.id}")
        print(f"Pages: {stored.page_count}")

        print("\n[2/5] Running document processing pipeline...")
        result = process_document(
            document_record=document,
            pdf_path=get_document_path(
                stored.storage_key,
                document_settings,
            ),
            db=db,
            document_settings=document_settings,
            ocr_settings=load_ocr_settings(),
        )

        print(f"Processing status: {result.status}")
        print(f"Extraction method: {result.extraction_method}")
        print(f"Processing duration: {result.processing_duration_seconds:.2f}s")

        db.expire_all()

        document = db.get(Document, stored.document_id)

        print("\n[3/5] Checking PostgreSQL persistence...")
        chunk_count = db.execute(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == stored.document_id)
        ).scalar_one()

        embedding_count = db.execute(
            select(func.count())
            .select_from(ChunkEmbedding)
            .join(
                DocumentChunk,
                ChunkEmbedding.chunk_id == DocumentChunk.id,
            )
            .where(
                DocumentChunk.document_id == stored.document_id
            )
        ).scalar_one()

        print(f"Document status: {document.processing_status}")
        print(f"Persisted chunks: {chunk_count}")
        print(f"Persisted embeddings: {embedding_count}")

        ready_count = db.execute(
            select(func.count())
            .select_from(ChunkEmbedding)
            .join(
                DocumentChunk,
                ChunkEmbedding.chunk_id == DocumentChunk.id,
            )
            .where(
                DocumentChunk.document_id == stored.document_id,
                ChunkEmbedding.status == "ready",
            )
        ).scalar_one()

        print(f"Ready embeddings: {ready_count}")

        print("\n[4/5] Validating embedding configuration...")
        from app.core.embedding_config import get_embedding_settings

        embedding_settings = get_embedding_settings()

        print(f"Provider: {embedding_settings.provider}")
        print(f"Model: {embedding_settings.model}")
        print(f"Dimensions: {embedding_settings.dimensions}")

        print("\n[5/5] Verification summary")
        checks = {
            "Document processing completed": (
                document.processing_status == "completed"
            ),
            "Chunks persisted": chunk_count > 0,
            "Embeddings persisted": embedding_count > 0,
            "Ready embeddings exist": ready_count > 0,
            "Embedding dimensions are 1536": (
                embedding_settings.dimensions == 1536
            ),
        }

        for label, passed in checks.items():
            print(f"{'PASS' if passed else 'FAIL'} - {label}")

        if not all(checks.values()):
            raise RuntimeError(
                "Phase 8 real-data verification did not pass."
            )

        print("\nPHASE 8 REAL-PDF PIPELINE: PASSED")

    finally:
        db.close()


if __name__ == "__main__":
    main()