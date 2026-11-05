from __future__ import annotations

import math

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.embedding_config import (
    EmbeddingSettings,
    get_embedding_settings,
)

from app.models.chunk_embedding import ChunkEmbedding
from app.models.document_chunk import DocumentChunk

from app.services.embeddings.embedding_pipeline import (
    ChunkEmbeddingOutcome,
)


PIPELINE_VERSION = "1.0.0"
DATABASE_VECTOR_DIMENSIONS = 1536


class EmbeddingPersistenceError(Exception):
    """Base exception for embedding persistence errors."""


class EmbeddingPersistenceValidationError(
    EmbeddingPersistenceError
):
    """Raised when embedding data fails validation."""


@dataclass(frozen=True)
class EmbeddingPersistenceResult:
    total: int
    inserted: int
    updated: int
    unchanged: int
    failed: int


class EmbeddingPersistenceService:

    def __init__(
        self,
        settings: EmbeddingSettings | None = None,
    ) -> None:
        self.settings = settings or get_embedding_settings()

    def _validate_outcome(
        self,
        outcome: ChunkEmbeddingOutcome,
    ) -> None:

        if not outcome.chunk_id:
            raise EmbeddingPersistenceValidationError(
                "Chunk ID cannot be empty."
            )

        if not outcome.content_hash:
            raise EmbeddingPersistenceValidationError(
                "Content hash cannot be empty."
            )

        if outcome.status not in {"ready", "failed"}:
            raise EmbeddingPersistenceValidationError(
                "Unsupported embedding status."
            )

        if outcome.status == "failed":
            return

        embedding = outcome.embedding

        if embedding is None:
            raise EmbeddingPersistenceValidationError(
                "Ready embedding must contain a vector."
            )

        if embedding.dimensions != DATABASE_VECTOR_DIMENSIONS:
            raise EmbeddingPersistenceValidationError(
                "Embedding dimensions do not match database storage."
            )

        if len(embedding.vector) != DATABASE_VECTOR_DIMENSIONS:
            raise EmbeddingPersistenceValidationError(
                "Invalid embedding vector length."
            )

        if embedding.provider != self.settings.provider:
            raise EmbeddingPersistenceValidationError(
                "Embedding provider mismatch."
            )

        if embedding.model != self.settings.model:
            raise EmbeddingPersistenceValidationError(
                "Embedding model mismatch."
            )

        if not all(
            math.isfinite(float(value))
            for value in embedding.vector
        ):
            raise EmbeddingPersistenceValidationError(
                "Embedding contains non-finite values."
            )

    def _identity(
        self,
        outcome: ChunkEmbeddingOutcome,
    ) -> dict:

        embedding = outcome.embedding

        return {
            "chunk_id": outcome.chunk_id,
            "content_hash": outcome.content_hash,
            "provider": (
                embedding.provider
                if embedding is not None
                else self.settings.provider
            ),
            "model": (
                embedding.model
                if embedding is not None
                else self.settings.model
            ),
            "model_version": (
                embedding.model
                if embedding is not None
                else self.settings.model
            ),
            "dimensions": (
                embedding.dimensions
                if embedding is not None
                else DATABASE_VECTOR_DIMENSIONS
            ),
            "pipeline_version": PIPELINE_VERSION,
        }

    @staticmethod
    def _get_first(
        db: Session,
        statement,
    ):
        """Execute a SELECT and return its first scalar result."""
        return db.execute(statement).scalars().first()

    def _get_existing_embedding(
        self,
        db: Session,
        identity: dict,
    ) -> ChunkEmbedding | None:

        statement = select(ChunkEmbedding).where(
            ChunkEmbedding.chunk_id == identity["chunk_id"],
            ChunkEmbedding.content_hash == identity["content_hash"],
            ChunkEmbedding.provider == identity["provider"],
            ChunkEmbedding.model == identity["model"],
            ChunkEmbedding.model_version == identity["model_version"],
            ChunkEmbedding.dimensions == identity["dimensions"],
            ChunkEmbedding.pipeline_version == identity["pipeline_version"],
        )

        return self._get_first(db, statement)

    @staticmethod
    def _vector_values(
        embedding,
    ) -> list[float] | None:

        if embedding is None:
            return None

        return [
            float(value)
            for value in embedding
        ]

    def persist(
        self,
        db: Session,
        outcomes: Sequence[ChunkEmbeddingOutcome],
    ) -> EmbeddingPersistenceResult:

        if isinstance(outcomes, (str, bytes)):
            raise EmbeddingPersistenceValidationError(
                "Outcomes must be a sequence."
            )

        counters = {
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "failed": 0,
        }

        try:
            for outcome in outcomes:

                self._validate_outcome(outcome)

                chunk_statement = select(DocumentChunk).where(
                    DocumentChunk.chunk_id == outcome.chunk_id
                )

                chunk = self._get_first(
                    db,
                    chunk_statement,
                )

                if chunk is None:
                    raise EmbeddingPersistenceValidationError(
                        f"Chunk not found: {outcome.chunk_id}"
                    )

                if chunk.content_hash != outcome.content_hash:
                    raise EmbeddingPersistenceValidationError(
                        "Chunk content hash mismatch. "
                        "The chunk may have changed since embedding."
                    )

                identity = self._identity(outcome)

                existing = self._get_existing_embedding(
                    db,
                    identity,
                )

                if outcome.status == "failed":
                    counters["failed"] += 1

                # Do not replace a valid vector with a transient failure.
                if (
                    existing is not None
                    and existing.status == "ready"
                    and outcome.status == "failed"
                ):
                    counters["unchanged"] += 1
                    continue

                vector = (
                    list(outcome.embedding.vector)
                    if outcome.embedding is not None
                    else None
                )

                values = {
                    **identity,
                    "status": outcome.status,
                    "embedding": vector,
                    "error_code": (
                        outcome.error_code
                        if outcome.status == "failed"
                        else None
                    ),
                }

                if existing is not None:

                    current_vector = self._vector_values(
                        existing.embedding
                    )

                    unchanged = (
                        existing.status == values["status"]
                        and current_vector == values["embedding"]
                        and existing.error_code == values["error_code"]
                    )

                    if unchanged:
                        counters["unchanged"] += 1
                        continue

                    for field, value in values.items():
                        setattr(existing, field, value)

                    counters["updated"] += 1

                else:
                    db.add(
                        ChunkEmbedding(**values)
                    )
                    counters["inserted"] += 1

            db.flush()
            db.commit()

        except Exception:
            db.rollback()
            raise

        return EmbeddingPersistenceResult(
            total=len(outcomes),
            inserted=counters["inserted"],
            updated=counters["updated"],
            unchanged=counters["unchanged"],
            failed=counters["failed"],
        )