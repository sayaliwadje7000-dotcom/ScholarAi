from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy.orm import Session

from app.services.embeddings.embedding_service import (
    EmbeddingService,
)

from app.services.embeddings.resource_content import (
    ResourceContentBuilder,
)

from app.services.embeddings.resource_embedding_pipeline import (
    ResourceEmbeddingPipeline,
    ResourceEmbeddingPipelineResult,
)

from app.services.embeddings.resource_embedding_persistence import (
    ResourceEmbeddingPersistenceService,
    ResourceEmbeddingPersistenceResult,
)


@dataclass(frozen=True, slots=True)
class ResourceEmbeddingGenerationResult:
    pipeline: ResourceEmbeddingPipelineResult
    persistence: ResourceEmbeddingPersistenceResult


class ResourceEmbeddingService:
    """
    Coordinates resource representation, embedding generation,
    validation and database persistence.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        pipeline: ResourceEmbeddingPipeline | None = None,
        persistence: ResourceEmbeddingPersistenceService | None = None,
    ):
        self.embedding_service = (
            embedding_service or EmbeddingService()
        )

        self.content_builder = ResourceContentBuilder()

        self.pipeline = (
            pipeline
            or ResourceEmbeddingPipeline(
                embedding_service=self.embedding_service,
                content_builder=self.content_builder,
            )
        )

        self.persistence = (
            persistence
            or ResourceEmbeddingPersistenceService(
                settings=self.embedding_service.settings
            )
        )

    async def generate(
        self,
        db: Session,
        resources: Sequence,
    ) -> ResourceEmbeddingGenerationResult:

        pipeline_result = await self.pipeline.generate(
            resources
        )

        persistence_result = self.persistence.persist(
            db=db,
            outcomes=pipeline_result.outcomes,
        )

        return ResourceEmbeddingGenerationResult(
            pipeline=pipeline_result,
            persistence=persistence_result,
        )