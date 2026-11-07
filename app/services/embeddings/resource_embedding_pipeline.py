from __future__ import annotations

import asyncio
import math

from dataclasses import dataclass
from typing import Sequence

from app.schemas.embeddings import EmbeddingResult

from app.services.embeddings.embedding_service import (
    EmbeddingService,
)

from app.services.embeddings.resource_content import (
    ResourceContent,
    ResourceContentBuilder,
)


DATABASE_VECTOR_DIMENSIONS = 1536


@dataclass(frozen=True, slots=True)
class ResourceEmbeddingOutcome:
    resource_id: object
    content_hash: str
    status: str
    embedding: EmbeddingResult | None = None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class ResourceEmbeddingPipelineResult:
    total_resources: int
    successful_resources: int
    failed_resources: int
    outcomes: tuple[ResourceEmbeddingOutcome, ...]

    @property
    def success_rate(self) -> float:
        if self.total_resources == 0:
            return 0.0

        return (
            self.successful_resources
            / self.total_resources
        )


class ResourceEmbeddingPipeline:
    """
    Generates semantic embeddings for StudyResource objects.

    Responsibilities:
    - Build normalized resource representations.
    - Generate content hashes.
    - Call the existing EmbeddingService.
    - Validate generated vectors.
    - Track individual failures.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        content_builder: ResourceContentBuilder | None = None,
        max_concurrency: int = 5,
    ):
        if max_concurrency <= 0:
            raise ValueError(
                "Maximum concurrency must be positive."
            )

        self.embedding_service = embedding_service

        self.content_builder = (
            content_builder or ResourceContentBuilder()
        )

        self.max_concurrency = max_concurrency

        self._semaphore = asyncio.Semaphore(
            max_concurrency
        )

    @staticmethod
    def _validate_embedding(
        embedding: EmbeddingResult,
    ) -> None:
        if embedding.dimensions != DATABASE_VECTOR_DIMENSIONS:
            raise ValueError(
                "Embedding dimensions must equal 1536."
            )

        if len(embedding.vector) != DATABASE_VECTOR_DIMENSIONS:
            raise ValueError(
                "Invalid embedding vector length."
            )

        if not all(
            math.isfinite(float(value))
            for value in embedding.vector
        ):
            raise ValueError(
                "Embedding contains non-finite values."
            )

    async def _process_resource(
        self,
        resource,
    ) -> ResourceEmbeddingOutcome:

        content: ResourceContent | None = None

        try:
            content = self.content_builder.build(
                resource
            )

            async with self._semaphore:
                embedding = (
                    await self.embedding_service.embed_document(
                        content.text
                    )
                )

            self._validate_embedding(embedding)

            if embedding.provider != self.embedding_service.settings.provider:
                raise ValueError(
                    "Embedding provider mismatch."
                )

            if embedding.model != self.embedding_service.settings.model:
                raise ValueError(
                    "Embedding model mismatch."
                )

            return ResourceEmbeddingOutcome(
                resource_id=content.resource_id,
                content_hash=content.content_hash,
                status="ready",
                embedding=embedding,
            )

        except Exception as exc:
            resource_id = getattr(
                resource,
                "id",
                None,
            )

            return ResourceEmbeddingOutcome(
                resource_id=resource_id,
                content_hash=(
                    content.content_hash
                    if content is not None
                    else ""
                ),
                status="failed",
                error_code=type(exc).__name__,
            )

    async def generate(
        self,
        resources: Sequence,
    ) -> ResourceEmbeddingPipelineResult:

        if isinstance(resources, (str, bytes)):
            raise TypeError(
                "Resources must be a sequence."
            )

        if not isinstance(resources, Sequence):
            raise TypeError(
                "Resources must be a sequence."
            )

        if not resources:
            return ResourceEmbeddingPipelineResult(
                total_resources=0,
                successful_resources=0,
                failed_resources=0,
                outcomes=(),
            )

        outcomes = await asyncio.gather(
            *(
                self._process_resource(resource)
                for resource in resources
            )
        )

        successful = sum(
            outcome.status == "ready"
            for outcome in outcomes
        )

        return ResourceEmbeddingPipelineResult(
            total_resources=len(outcomes),
            successful_resources=successful,
            failed_resources=len(outcomes) - successful,
            outcomes=tuple(outcomes),
        )