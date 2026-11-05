import asyncio
import time

from dataclasses import dataclass
from typing import Sequence

from app.schemas.embeddings import EmbeddingResult
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.embeddings.metadata import compute_content_hash


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingOutcome:
    chunk_id: str
    content_hash: str
    status: str
    embedding: EmbeddingResult | None = None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingPipelineResult:
    total_chunks: int
    successful_chunks: int
    failed_chunks: int
    outcomes: tuple[ChunkEmbeddingOutcome, ...]
    provider: str
    model: str
    dimensions: int
    duration_seconds: float

    @property
    def success_rate(self) -> float:
        if self.total_chunks == 0:
            return 0.0

        return self.successful_chunks / self.total_chunks


class EmbeddingPipelineError(Exception):
    """Base exception for embedding pipeline failures."""


class EmbeddingPipelineInputError(EmbeddingPipelineError):
    """Raised when chunk input is invalid."""


class EmbeddingPipeline:
    """
    Generates embeddings for persistent document chunks.

    Responsibilities:
    - Validate chunk identity and content.
    - Verify deterministic content hashes.
    - Process chunks in bounded batches.
    - Reuse the existing EmbeddingService.
    - Track individual successes and failures.
    - Validate embedding metadata and dimensions.

    Database persistence is intentionally excluded.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        batch_size: int = 32,
    ):
        if batch_size <= 0:
            raise ValueError("Batch size must be positive.")

        self.embedding_service = embedding_service
        self.batch_size = batch_size

        self.settings = embedding_service.settings

    @staticmethod
    def _validate_chunks(chunks: Sequence) -> list:
        if isinstance(chunks, (str, bytes)):
            raise EmbeddingPipelineInputError(
                "Chunks must be a sequence of chunk objects."
            )

        if not isinstance(chunks, Sequence):
            raise EmbeddingPipelineInputError(
                "Chunks must be a sequence."
            )

        validated = list(chunks)

        seen_ids = set()

        for chunk in validated:
            chunk_id = getattr(chunk, "chunk_id", None)
            text = getattr(chunk, "text", None)
            content_hash = getattr(chunk, "content_hash", None)

            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise EmbeddingPipelineInputError(
                    "Every chunk must have a valid chunk_id."
                )

            if chunk_id in seen_ids:
                raise EmbeddingPipelineInputError(
                    f"Duplicate chunk identifier: {chunk_id}"
                )

            seen_ids.add(chunk_id)

            if not isinstance(text, str) or not text.strip():
                raise EmbeddingPipelineInputError(
                    f"Chunk {chunk_id} has empty or invalid text."
                )

            if not isinstance(content_hash, str):
                raise EmbeddingPipelineInputError(
                    f"Chunk {chunk_id} has an invalid content hash."
                )

            expected_hash = compute_content_hash(text)

            if content_hash != expected_hash:
                raise EmbeddingPipelineInputError(
                    f"Content hash mismatch for chunk {chunk_id}."
                )

        return validated

    def _validate_embedding(
        self,
        result: EmbeddingResult,
    ) -> None:

        if not isinstance(result, EmbeddingResult):
            raise TypeError(
                "Embedding service returned an invalid result."
            )

        if result.dimensions != self.settings.dimensions:
            raise ValueError(
                "Embedding dimensions do not match configured dimensions."
            )

        if result.model != self.settings.model:
            raise ValueError(
                "Embedding model does not match configured model."
            )

        if result.provider != self.settings.provider:
            raise ValueError(
                "Embedding provider does not match configured provider."
            )

        if len(result.vector) != self.settings.dimensions:
            raise ValueError(
                "Embedding vector length is invalid."
            )

    async def _process_chunk(
        self,
        chunk,
    ) -> ChunkEmbeddingOutcome:

        chunk_id = chunk.chunk_id
        content_hash = chunk.content_hash

        try:
            embedding = await self.embedding_service.embed_document(
                chunk.text
            )

            self._validate_embedding(embedding)

            return ChunkEmbeddingOutcome(
                chunk_id=chunk_id,
                content_hash=content_hash,
                status="ready",
                embedding=embedding,
            )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            return ChunkEmbeddingOutcome(
                chunk_id=chunk_id,
                content_hash=content_hash,
                status="failed",
                error_code=type(exc).__name__,
            )

    async def generate(
        self,
        chunks: Sequence,
    ) -> EmbeddingPipelineResult:
        """
        Generate embeddings for a collection of document chunks.

        Results preserve the original input order.
        Individual chunk failures do not terminate the pipeline.
        """

        started_at = time.perf_counter()

        validated_chunks = self._validate_chunks(chunks)

        if not validated_chunks:
            return EmbeddingPipelineResult(
                total_chunks=0,
                successful_chunks=0,
                failed_chunks=0,
                outcomes=(),
                provider=self.settings.provider,
                model=self.settings.model,
                dimensions=self.settings.dimensions,
                duration_seconds=0.0,
            )

        outcomes = []

        for start in range(
            0,
            len(validated_chunks),
            self.batch_size,
        ):
            batch = validated_chunks[
                start:start + self.batch_size
            ]

            batch_results = await asyncio.gather(
                *(
                    self._process_chunk(chunk)
                    for chunk in batch
                )
            )

            outcomes.extend(batch_results)

        successful = sum(
            outcome.status == "ready"
            for outcome in outcomes
        )

        failed = len(outcomes) - successful

        duration = time.perf_counter() - started_at

        return EmbeddingPipelineResult(
            total_chunks=len(validated_chunks),
            successful_chunks=successful,
            failed_chunks=failed,
            outcomes=tuple(outcomes),
            provider=self.settings.provider,
            model=self.settings.model,
            dimensions=self.settings.dimensions,
            duration_seconds=round(duration, 6),
        )