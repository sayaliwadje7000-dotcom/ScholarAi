from __future__ import annotations

import math
import uuid

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.chunk_embedding import ChunkEmbedding
from app.models.document_chunk import DocumentChunk


DATABASE_VECTOR_DIMENSIONS = 1536

DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 100


class SemanticSearchError(Exception):
    """Base exception for semantic search operations."""


class SemanticSearchValidationError(SemanticSearchError):
    """Raised when search input or filters are invalid."""


@dataclass(frozen=True)
class SemanticSearchResult:
    chunk_id: str
    document_id: uuid.UUID
    chunk_index: int
    text: str

    page_numbers: list[int]
    start_page: int | None
    end_page: int | None

    similarity: float
    distance: float

    provider: str
    model: str
    dimensions: int
    pipeline_version: str
    chunking_version: str


class SemanticSearchService:
    """
    PostgreSQL pgvector semantic retrieval service.

    Uses cosine distance to identify the most relevant
    document chunks.

    Supports metadata filtering by:
    - Document ID
    - Multiple document IDs
    - Chunking version
    - Embedding provider
    - Embedding model
    - Pipeline version
    """

    def __init__(
        self,
        vector_dimensions: int = DATABASE_VECTOR_DIMENSIONS,
        default_limit: int = DEFAULT_SEARCH_LIMIT,
        max_limit: int = MAX_SEARCH_LIMIT,
    ) -> None:

        if vector_dimensions != DATABASE_VECTOR_DIMENSIONS:
            raise SemanticSearchValidationError(
                "Configured dimensions must match the database "
                f"VECTOR({DATABASE_VECTOR_DIMENSIONS}) column."
            )

        if default_limit < 1:
            raise SemanticSearchValidationError(
                "Default search limit must be positive."
            )

        if max_limit < default_limit:
            raise SemanticSearchValidationError(
                "Maximum limit cannot be smaller than default limit."
            )

        self.vector_dimensions = vector_dimensions
        self.default_limit = default_limit
        self.max_limit = max_limit

    def _validate_vector(
        self,
        query_vector: Sequence[float],
    ) -> list[float]:

        if isinstance(query_vector, (str, bytes)):
            raise SemanticSearchValidationError(
                "Query embedding must be a numeric sequence."
            )

        if not isinstance(query_vector, Sequence):
            raise SemanticSearchValidationError(
                "Query embedding must be a sequence."
            )

        if len(query_vector) != self.vector_dimensions:
            raise SemanticSearchValidationError(
                f"Expected {self.vector_dimensions} dimensions, "
                f"received {len(query_vector)}."
            )

        vector: list[float] = []

        for value in query_vector:

            if isinstance(value, bool) or not isinstance(
                value, (int, float)
            ):
                raise SemanticSearchValidationError(
                    "Embedding contains a non-numeric value."
                )

            if not math.isfinite(value):
                raise SemanticSearchValidationError(
                    "Embedding contains a non-finite value."
                )

            vector.append(float(value))

        return vector

    def _validate_filters(
        self,
        document_id: uuid.UUID | None,
        document_ids: Sequence[uuid.UUID] | None,
        min_similarity: float | None,
    ) -> None:

        if document_id is not None and not isinstance(
            document_id, uuid.UUID
        ):
            raise SemanticSearchValidationError(
                "Document ID must be a UUID."
            )

        if document_ids is not None:

            if isinstance(document_ids, (str, bytes)):
                raise SemanticSearchValidationError(
                    "Document IDs must be a sequence."
                )

            if not isinstance(document_ids, Sequence):
                raise SemanticSearchValidationError(
                    "Document IDs must be a sequence."
                )

            if not document_ids:
                raise SemanticSearchValidationError(
                    "Document IDs cannot be empty."
                )

            if any(
                not isinstance(item, uuid.UUID)
                for item in document_ids
            ):
                raise SemanticSearchValidationError(
                    "Every document ID must be a UUID."
                )

            if len(set(document_ids)) != len(document_ids):
                raise SemanticSearchValidationError(
                    "Duplicate document IDs are not allowed."
                )

        if document_id is not None and document_ids is not None:
            raise SemanticSearchValidationError(
                "Use document_id or document_ids, not both."
            )

        if min_similarity is not None:

            if isinstance(min_similarity, bool) or not isinstance(
                min_similarity, (int, float)
            ):
                raise SemanticSearchValidationError(
                    "Minimum similarity must be numeric."
                )

            if not math.isfinite(min_similarity):
                raise SemanticSearchValidationError(
                    "Minimum similarity must be finite."
                )

            if not -1.0 <= min_similarity <= 1.0:
                raise SemanticSearchValidationError(
                    "Minimum similarity must be between -1 and 1."
                )

    def search(
        self,
        db: Session,
        query_vector: Sequence[float],
        *,
        limit: int | None = None,
        document_id: uuid.UUID | None = None,
        document_ids: Sequence[uuid.UUID] | None = None,
        chunking_version: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        pipeline_version: str | None = None,
        min_similarity: float | None = None,
    ) -> list[SemanticSearchResult]:

        # Validate query embedding.
        vector = self._validate_vector(query_vector)

        # Validate document filters.
        self._validate_filters(
            document_id,
            document_ids,
            min_similarity,
        )

        # Validate result limit.
        if limit is None:
            limit = self.default_limit

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise SemanticSearchValidationError(
                "Search limit must be an integer."
            )

        if not 1 <= limit <= self.max_limit:
            raise SemanticSearchValidationError(
                f"Search limit must be between 1 and {self.max_limit}."
            )

        # Validate metadata filters.
        if chunking_version is not None and (
            not isinstance(chunking_version, str)
            or not chunking_version.strip()
        ):
            raise SemanticSearchValidationError(
                "Chunking version cannot be empty."
            )

        if provider is not None and (
            not isinstance(provider, str) or not provider.strip()
        ):
            raise SemanticSearchValidationError(
                "Provider cannot be empty."
            )

        if model is not None and (
            not isinstance(model, str) or not model.strip()
        ):
            raise SemanticSearchValidationError(
                "Model cannot be empty."
            )

        if pipeline_version is not None and (
            not isinstance(pipeline_version, str)
            or not pipeline_version.strip()
        ):
            raise SemanticSearchValidationError(
                "Pipeline version cannot be empty."
            )

        # Calculate cosine distance using pgvector.
        distance_expression = (
            ChunkEmbedding.embedding
            .cosine_distance(vector)
            .label("distance")
        )

        # Base semantic search query.
        statement = (
            select(
                DocumentChunk,
                ChunkEmbedding,
                distance_expression,
            )
            .join(
                ChunkEmbedding,
                and_(
                    ChunkEmbedding.chunk_id == DocumentChunk.chunk_id,
                    ChunkEmbedding.content_hash
                    == DocumentChunk.content_hash,
                ),
            )
            .where(
                ChunkEmbedding.status == "ready",
                ChunkEmbedding.embedding.is_not(None),
                ChunkEmbedding.dimensions == self.vector_dimensions,
            )
        )

        # Filter by one document.
        if document_id is not None:
            statement = statement.where(
                DocumentChunk.document_id == document_id
            )

        # Filter by multiple documents.
        if document_ids is not None:
            statement = statement.where(
                DocumentChunk.document_id.in_(document_ids)
            )

        # Filter by chunking version.
        if chunking_version is not None:
            statement = statement.where(
                DocumentChunk.chunking_version == chunking_version
            )

        # Filter by embedding provider.
        if provider is not None:
            statement = statement.where(
                ChunkEmbedding.provider == provider
            )

        # Filter by embedding model.
        if model is not None:
            statement = statement.where(
                ChunkEmbedding.model == model
            )

        # Filter by embedding pipeline version.
        if pipeline_version is not None:
            statement = statement.where(
                ChunkEmbedding.pipeline_version == pipeline_version
            )

        # Cosine similarity = 1 - cosine distance.
        if min_similarity is not None:
            statement = statement.where(
                distance_expression <= 1.0 - min_similarity
            )

        # Return the closest matching chunks first.
        statement = (
            statement
            .order_by(distance_expression.asc())
            .limit(limit)
        )

        rows = db.execute(statement).all()

        results: list[SemanticSearchResult] = []

        for chunk, embedding, distance in rows:

            distance = float(distance)
            similarity = 1.0 - distance

            results.append(
                SemanticSearchResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    page_numbers=chunk.page_numbers or [],
                    start_page=chunk.start_page,
                    end_page=chunk.end_page,
                    similarity=similarity,
                    distance=distance,
                    provider=embedding.provider,
                    model=embedding.model,
                    dimensions=embedding.dimensions,
                    pipeline_version=embedding.pipeline_version,
                    chunking_version=chunk.chunking_version,
                )
            )

        return results