from __future__ import annotations

import asyncio
import logging

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.embedding_config import (
    get_embedding_settings,
)

from app.models.chunk_embedding import ChunkEmbedding
from app.models.document_chunk import DocumentChunk

from app.services.document_chunking_service import (
    DocumentChunkingResult,
)

from app.services.embeddings.embedding_service import (
    EmbeddingService,
)

from app.services.embeddings.embedding_pipeline import (
    EmbeddingPipeline,
)

from app.services.embeddings.embedding_persistence import (
    EmbeddingPersistenceService,
)

from app.services.embeddings.metadata import (
    compute_content_hash,
)


logger = logging.getLogger(__name__)

CHUNKING_VERSION = "1.0"
EMBEDDING_PIPELINE_VERSION = "1.0.0"
DATABASE_VECTOR_DIMENSIONS = 1536


class DocumentChunkPersistenceError(Exception):
    """Raised when document chunks cannot be persisted."""


@dataclass(frozen=True)
class DocumentIndexingResult:
    total_chunks: int
    persisted_chunks: int
    embeddings_generated: int
    embeddings_ready: int
    embeddings_failed: int
    embeddings_skipped: int
    indexing_error: str | None = None


def persist_document_chunks(
    db: Session,
    result: DocumentChunkingResult,
) -> list[DocumentChunk]:
    """
    Persist chunking results into PostgreSQL.

    Existing chunks are updated.
    Obsolete chunks are deleted.
    Existing embeddings are preserved for unchanged chunks.
    """

    if not isinstance(result, DocumentChunkingResult):
        raise DocumentChunkPersistenceError(
            "A valid document chunking result is required."
        )

    try:
        document_id = UUID(result.document_id)

        existing_chunks = list(
            db.scalars(
                select(DocumentChunk).where(
                    DocumentChunk.document_id == document_id
                )
            ).all()
        )

        desired_ids = set()
        desired_indices = set()

        prepared_chunks = []

        for chunk in result.chunks:

            if UUID(chunk.document_id) != document_id:
                raise DocumentChunkPersistenceError(
                    "Chunk document ownership mismatch."
                )

            if (
                not isinstance(chunk.chunk_id, str)
                or len(chunk.chunk_id) != 64
            ):
                raise DocumentChunkPersistenceError(
                    "Invalid chunk identifier."
                )

            if chunk.chunk_id in desired_ids:
                raise DocumentChunkPersistenceError(
                    "Duplicate chunk identifier."
                )

            if chunk.chunk_index in desired_indices:
                raise DocumentChunkPersistenceError(
                    "Duplicate chunk index."
                )

            if not isinstance(chunk.text, str) or not chunk.text.strip():
                raise DocumentChunkPersistenceError(
                    "Chunk text cannot be empty."
                )

            content_hash = compute_content_hash(chunk.text)

            desired_ids.add(chunk.chunk_id)
            desired_indices.add(chunk.chunk_index)

            prepared_chunks.append(
                (chunk, content_hash)
            )

        existing_by_id = {
            chunk.chunk_id: chunk
            for chunk in existing_chunks
        }

        # Remove obsolete chunks before inserting replacements.
        # This avoids conflicts with the unique document/index constraint.
        for existing in existing_chunks:

            if existing.chunk_id not in desired_ids:
                db.delete(existing)

        db.flush()

        for chunk, content_hash in prepared_chunks:

            existing = existing_by_id.get(chunk.chunk_id)

            if existing is not None:

                # Remove old vectors if the text hash changed.
                if existing.content_hash != content_hash:

                    db.execute(
                        delete(ChunkEmbedding).where(
                            ChunkEmbedding.chunk_id == chunk.chunk_id
                        )
                    )

                existing.document_id = document_id
                existing.chunk_index = chunk.chunk_index
                existing.text = chunk.text
                existing.content_hash = content_hash
                existing.page_numbers = list(chunk.page_numbers)
                existing.start_page = chunk.start_page
                existing.end_page = chunk.end_page
                existing.character_count = chunk.character_count
                existing.word_count = chunk.word_count
                existing.chunking_version = CHUNKING_VERSION

            else:

                db.add(
                    DocumentChunk(
                        chunk_id=chunk.chunk_id,
                        document_id=document_id,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        content_hash=content_hash,
                        page_numbers=list(chunk.page_numbers),
                        start_page=chunk.start_page,
                        end_page=chunk.end_page,
                        character_count=chunk.character_count,
                        word_count=chunk.word_count,
                        chunking_version=CHUNKING_VERSION,
                    )
                )

        db.flush()
        db.commit()

        return list(
            db.scalars(
                select(DocumentChunk)
                .where(
                    DocumentChunk.document_id == document_id
                )
                .order_by(DocumentChunk.chunk_index)
            ).all()
        )

    except Exception as exc:

        db.rollback()

        if isinstance(exc, DocumentChunkPersistenceError):
            raise

        raise DocumentChunkPersistenceError(
            "Unable to persist document chunks."
        ) from exc


def _find_chunks_requiring_embeddings(
    db: Session,
    chunks: list[DocumentChunk],
) -> list[DocumentChunk]:
    """
    Return chunks without a valid embedding for the active model.
    """

    if not chunks:
        return []

    settings = get_embedding_settings()

    chunk_ids = [
        chunk.chunk_id
        for chunk in chunks
    ]

    ready_embeddings = db.scalars(
        select(ChunkEmbedding).where(
            ChunkEmbedding.chunk_id.in_(chunk_ids),
            ChunkEmbedding.provider == settings.provider,
            ChunkEmbedding.model == settings.model,
            ChunkEmbedding.dimensions == settings.dimensions,
            ChunkEmbedding.pipeline_version == EMBEDDING_PIPELINE_VERSION,
            ChunkEmbedding.status == "ready",
            ChunkEmbedding.embedding.is_not(None),
        )
    ).all()

    ready_keys = {
        (item.chunk_id, item.content_hash)
        for item in ready_embeddings
    }

    return [
        chunk
        for chunk in chunks
        if (chunk.chunk_id, chunk.content_hash) not in ready_keys
    ]


def index_document_chunks(
    db: Session,
    chunking_result: DocumentChunkingResult,
    batch_size: int = 32,
) -> DocumentIndexingResult:
    """
    Complete document indexing:

    1. Persist chunks.
    2. Find chunks requiring embeddings.
    3. Generate embeddings.
    4. Persist embedding outcomes.

    Embedding failures do not invalidate successful PDF processing.
    """

    persisted_chunks = persist_document_chunks(
        db=db,
        result=chunking_result,
    )

    total_chunks = len(persisted_chunks)

    if not persisted_chunks:

        return DocumentIndexingResult(
            total_chunks=0,
            persisted_chunks=0,
            embeddings_generated=0,
            embeddings_ready=0,
            embeddings_failed=0,
            embeddings_skipped=0,
        )

    pending_chunks = _find_chunks_requiring_embeddings(
        db=db,
        chunks=persisted_chunks,
    )

    skipped = total_chunks - len(pending_chunks)

    if not pending_chunks:

        return DocumentIndexingResult(
            total_chunks=total_chunks,
            persisted_chunks=total_chunks,
            embeddings_generated=0,
            embeddings_ready=0,
            embeddings_failed=0,
            embeddings_skipped=skipped,
        )

    embedding_service = None

    try:

        settings = get_embedding_settings()

        embedding_service = EmbeddingService(
            settings=settings,
        )

        pipeline = EmbeddingPipeline(
            embedding_service=embedding_service,
            batch_size=batch_size,
        )

        async def generate_embeddings():

            try:
                return await pipeline.generate(
                    pending_chunks
                )

            finally:

                try:
                    await embedding_service.close()

                except Exception:
                    logger.exception(
                        "Unable to close embedding provider."
                    )

        # This function is called from the synchronous
        # document-processing background worker.
        pipeline_result = asyncio.run(
            generate_embeddings()
        )

        persistence_result = EmbeddingPersistenceService(
            settings=settings
        ).persist(
            db=db,
            outcomes=pipeline_result.outcomes,
        )

        return DocumentIndexingResult(
            total_chunks=total_chunks,
            persisted_chunks=total_chunks,
            embeddings_generated=pipeline_result.total_chunks,
            embeddings_ready=pipeline_result.successful_chunks,
            embeddings_failed=persistence_result.failed,
            embeddings_skipped=skipped,
        )

    except Exception as exc:

        logger.exception(
            "Embedding indexing failed for document %s.",
            chunking_result.document_id,
        )

        return DocumentIndexingResult(
            total_chunks=total_chunks,
            persisted_chunks=total_chunks,
            embeddings_generated=0,
            embeddings_ready=0,
            embeddings_failed=0,
            embeddings_skipped=skipped,
            indexing_error=type(exc).__name__,
        )