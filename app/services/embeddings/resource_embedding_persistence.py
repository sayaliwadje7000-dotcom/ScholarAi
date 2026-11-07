from __future__ import annotations

import math

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.embedding_config import (
    EmbeddingSettings,
    get_embedding_settings,
)

from app.models.resource_embedding import (
    ResourceEmbedding,
    RESOURCE_EMBEDDING_PIPELINE_VERSION,
)

from app.services.embeddings.resource_embedding_pipeline import (
    ResourceEmbeddingOutcome,
)


DATABASE_VECTOR_DIMENSIONS = 1536


class ResourceEmbeddingPersistenceError(Exception):
    pass


class ResourceEmbeddingPersistenceValidationError(
    ResourceEmbeddingPersistenceError
):
    pass


@dataclass(frozen=True, slots=True)
class ResourceEmbeddingPersistenceResult:
    total: int
    inserted: int
    updated: int
    unchanged: int
    failed: int


class ResourceEmbeddingPersistenceService:

    def __init__(
        self,
        settings: EmbeddingSettings | None = None,
    ):
        self.settings = (
            settings or get_embedding_settings()
        )

        if self.settings.provider != "gemini":
            raise ValueError(
                "Unsupported resource embedding provider."
            )

    def _validate(
        self,
        outcome: ResourceEmbeddingOutcome,
    ) -> None:

        if outcome.resource_id is None:
            raise ResourceEmbeddingPersistenceValidationError(
                "Resource ID cannot be empty."
            )

        if outcome.status not in {"ready", "failed"}:
            raise ResourceEmbeddingPersistenceValidationError(
                "Invalid embedding status."
            )

        if not outcome.content_hash:
            raise ResourceEmbeddingPersistenceValidationError(
                "Content hash cannot be empty."
            )

        if outcome.status == "failed":
            return

        embedding = outcome.embedding

        if embedding is None:
            raise ResourceEmbeddingPersistenceValidationError(
                "Ready outcome must contain an embedding."
            )

        if embedding.dimensions != DATABASE_VECTOR_DIMENSIONS:
            raise ResourceEmbeddingPersistenceValidationError(
                "Embedding dimensions must equal 1536."
            )

        if len(embedding.vector) != DATABASE_VECTOR_DIMENSIONS:
            raise ResourceEmbeddingPersistenceValidationError(
                "Invalid embedding vector length."
            )

        if embedding.provider != self.settings.provider:
            raise ResourceEmbeddingPersistenceValidationError(
                "Embedding provider mismatch."
            )

        if embedding.model != self.settings.model:
            raise ResourceEmbeddingPersistenceValidationError(
                "Embedding model mismatch."
            )

        if not all(
            math.isfinite(float(value))
            for value in embedding.vector
        ):
            raise ResourceEmbeddingPersistenceValidationError(
                "Embedding contains non-finite values."
            )

    def _identity(
        self,
        outcome: ResourceEmbeddingOutcome,
    ) -> dict:

        embedding = outcome.embedding

        return {
            "resource_id": outcome.resource_id,
            "content_hash": outcome.content_hash,
            "provider": (
                embedding.provider
                if embedding
                else self.settings.provider
            ),
            "model": (
                embedding.model
                if embedding
                else self.settings.model
            ),
            "model_version": (
                embedding.model
                if embedding
                else self.settings.model
            ),
            "dimensions": (
                embedding.dimensions
                if embedding
                else DATABASE_VECTOR_DIMENSIONS
            ),
            "pipeline_version": (
                RESOURCE_EMBEDDING_PIPELINE_VERSION
            ),
        }

    def persist(
        self,
        db: Session,
        outcomes: tuple[ResourceEmbeddingOutcome, ...],
    ) -> ResourceEmbeddingPersistenceResult:

        inserted = 0
        updated = 0
        unchanged = 0
        failed = 0

        try:
            for outcome in outcomes:
                self._validate(outcome)

                identity = self._identity(outcome)

                existing = db.execute(
                    select(ResourceEmbedding).where(
                        ResourceEmbedding.resource_id
                        == identity["resource_id"],
                        ResourceEmbedding.content_hash
                        == identity["content_hash"],
                        ResourceEmbedding.provider
                        == identity["provider"],
                        ResourceEmbedding.model
                        == identity["model"],
                        ResourceEmbedding.model_version
                        == identity["model_version"],
                        ResourceEmbedding.dimensions
                        == identity["dimensions"],
                        ResourceEmbedding.pipeline_version
                        == identity["pipeline_version"],
                    )
                ).scalars().first()

                # A new content hash makes previous versions stale.
                db.execute(
                    update(ResourceEmbedding)
                    .where(
                        ResourceEmbedding.resource_id
                        == identity["resource_id"],
                        ResourceEmbedding.content_hash
                        != identity["content_hash"],
                        ResourceEmbedding.status == "ready",
                    )
                    .values(status="stale")
                )

                vector = (
                    list(outcome.embedding.vector)
                    if outcome.embedding is not None
                    else None
                )

                if existing is not None:
                    if (
                        existing.status == outcome.status
                        and existing.embedding == vector
                        and existing.error_code == outcome.error_code
                    ):
                        unchanged += 1
                        continue

                    existing.status = outcome.status
                    existing.embedding = vector
                    existing.error_code = outcome.error_code

                    updated += 1

                else:
                    record = ResourceEmbedding(
                        **identity,
                        status=outcome.status,
                        embedding=vector,
                        error_code=outcome.error_code,
                    )

                    db.add(record)
                    inserted += 1

                if outcome.status == "failed":
                    failed += 1

            # Flush only. Transaction commit belongs to the caller.
            db.flush()

        except Exception as exc:
            db.rollback()

            if isinstance(
                exc,
                ResourceEmbeddingPersistenceError,
            ):
                raise

            raise ResourceEmbeddingPersistenceError(
                "Failed to persist resource embeddings."
            ) from exc

        return ResourceEmbeddingPersistenceResult(
            total=len(outcomes),
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
            failed=failed,
        )