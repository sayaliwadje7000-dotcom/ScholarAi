from __future__ import annotations

import math

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.embedding_config import (
    EmbeddingSettings,
    get_embedding_settings,
)

from app.models.resource_embedding import (
    ResourceEmbedding,
    RESOURCE_EMBEDDING_PIPELINE_VERSION,
    VECTOR_DIMENSIONS,
)

from app.models.study_resource import StudyResource

from app.services.recommendations.content_based.similarity_models import (
    ResourceSimilarityResult,
    ResourceComparisonResult,
)


class ResourceSimilarityError(Exception):
    """Base exception for resource similarity operations."""


class ResourceSimilarityValidationError(
    ResourceSimilarityError
):
    """Raised when similarity input is invalid."""


class ResourceEmbeddingNotFoundError(
    ResourceSimilarityError
):
    """Raised when a usable resource embedding is unavailable."""


class ResourceSimilarityService:
    """
    Computes semantic similarity between educational resources.

    Uses PostgreSQL pgvector cosine distance.

    Responsibilities:
    - Validate embedding vectors.
    - Retrieve compatible resource embeddings.
    - Compute cosine similarity.
    - Find nearest educational resources.
    - Compare two individual resources.
    - Apply recommendation-oriented filters.
    """

    def __init__(
        self,
        settings: EmbeddingSettings | None = None,
    ) -> None:

        self.settings = (
            settings or get_embedding_settings()
        )

        if self.settings.dimensions != VECTOR_DIMENSIONS:
            raise ResourceSimilarityValidationError(
                "Configured embedding dimensions must equal "
                f"{VECTOR_DIMENSIONS}."
            )

    # ---------------------------------------------------------
    # Vector validation
    # ---------------------------------------------------------

    @staticmethod
    def validate_vector(
        vector: Sequence[float],
    ) -> list[float]:
        """
        Validate and normalize the input representation
        of a vector for database querying.
        """

        if isinstance(vector, (str, bytes)):
            raise ResourceSimilarityValidationError(
                "Embedding vector must be a numeric sequence."
            )

        if not isinstance(vector, Sequence):
            raise ResourceSimilarityValidationError(
                "Embedding vector must be a sequence."
            )

        if len(vector) != VECTOR_DIMENSIONS:
            raise ResourceSimilarityValidationError(
                f"Embedding vector must contain "
                f"{VECTOR_DIMENSIONS} dimensions."
            )

        validated = []

        for value in vector:

            if isinstance(value, bool):
                raise ResourceSimilarityValidationError(
                    "Boolean values are not valid vector elements."
                )

            try:
                number = float(value)

            except (TypeError, ValueError, OverflowError) as exc:
                raise ResourceSimilarityValidationError(
                    "Embedding vector contains a non-numeric value."
                ) from exc

            if not math.isfinite(number):
                raise ResourceSimilarityValidationError(
                    "Embedding vector contains a non-finite value."
                )

            validated.append(number)

        return validated

    # ---------------------------------------------------------
    # Similarity conversion
    # ---------------------------------------------------------

    @staticmethod
    def distance_to_similarity(
        distance: float,
    ) -> float:
        """
        Convert cosine distance into cosine similarity.

        pgvector cosine distance:
            distance = 1 - cosine_similarity

        Therefore:
            similarity = 1 - distance

        The theoretical cosine similarity range is [-1, 1].
        """

        distance = float(distance)

        if not math.isfinite(distance):
            raise ResourceSimilarityValidationError(
                "Cosine distance must be finite."
            )

        if distance < 0.0 or distance > 2.0:
            raise ResourceSimilarityValidationError(
                "Cosine distance must be between 0 and 2."
            )

        similarity = 1.0 - distance

        return max(-1.0, min(1.0, similarity))

    # ---------------------------------------------------------
    # Embedding identity filters
    # ---------------------------------------------------------

    def _compatible_embedding_filters(self):
        """
        Restrict searches to compatible, current embeddings.
        """

        return (
            ResourceEmbedding.status == "ready",
            ResourceEmbedding.provider == self.settings.provider,
            ResourceEmbedding.model == self.settings.model,
            ResourceEmbedding.dimensions == VECTOR_DIMENSIONS,
            ResourceEmbedding.pipeline_version
            == RESOURCE_EMBEDDING_PIPELINE_VERSION,
        )

    # ---------------------------------------------------------
    # Similar resource search
    # ---------------------------------------------------------

    def find_similar_resources(
        self,
        db: Session,
        query_vector: Sequence[float],
        limit: int = 10,
        min_similarity: float = 0.0,
        exclude_resource_id: UUID | None = None,
        subject: str | None = None,
        resource_type: str | None = None,
        language: str | None = None,
    ) -> list[ResourceSimilarityResult]:
        """
        Find educational resources closest to a query vector.

        Filtering is performed by PostgreSQL before results
        are returned to the application.
        """

        vector = self.validate_vector(query_vector)

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ResourceSimilarityValidationError(
                "Limit must be an integer."
            )

        if not 1 <= limit <= 100:
            raise ResourceSimilarityValidationError(
                "Limit must be between 1 and 100."
            )

        if isinstance(min_similarity, bool):
            raise ResourceSimilarityValidationError(
                "Minimum similarity must be numeric."
            )

        try:
            min_similarity = float(min_similarity)

        except (TypeError, ValueError, OverflowError) as exc:
            raise ResourceSimilarityValidationError(
                "Minimum similarity must be numeric."
            ) from exc

        if (
            not math.isfinite(min_similarity)
            or not -1.0 <= min_similarity <= 1.0
        ):
            raise ResourceSimilarityValidationError(
                "Minimum similarity must be between -1 and 1."
            )

        distance_expression = (
            ResourceEmbedding.embedding.cosine_distance(
                vector
            )
        )

        statement = (
            select(
                StudyResource,
                ResourceEmbedding.id.label("embedding_id"),
                distance_expression.label("cosine_distance"),
            )
            .join(
                ResourceEmbedding,
                ResourceEmbedding.resource_id
                == StudyResource.id,
            )
            .where(
                StudyResource.is_active.is_(True),
                *self._compatible_embedding_filters(),
            )
        )

        if exclude_resource_id is not None:

            statement = statement.where(
                StudyResource.id != exclude_resource_id
            )

        if subject is not None:

            statement = statement.where(
                StudyResource.subject == subject
            )

        if resource_type is not None:

            statement = statement.where(
                StudyResource.resource_type == resource_type
            )

        if language is not None:

            statement = statement.where(
                StudyResource.language == language
            )

        statement = (
            statement
            .order_by(distance_expression.asc())
            .limit(limit)
        )

        rows = db.execute(statement).all()

        results = []

        for resource, embedding_id, distance in rows:

            distance = float(distance)

            similarity = self.distance_to_similarity(
                distance
            )

            if similarity < min_similarity:
                continue

            results.append(
                ResourceSimilarityResult(
                    resource_id=resource.id,
                    resource=resource,
                    embedding_id=embedding_id,
                    cosine_distance=distance,
                    similarity_score=similarity,
                )
            )

        return results

    # ---------------------------------------------------------
    # Retrieve an individual resource embedding
    # ---------------------------------------------------------

    def get_resource_embedding(
        self,
        db: Session,
        resource_id: UUID,
    ) -> ResourceEmbedding:

        if not isinstance(resource_id, UUID):
            raise ResourceSimilarityValidationError(
                "Resource ID must be a UUID."
            )

        statement = (
            select(ResourceEmbedding)
            .where(
                ResourceEmbedding.resource_id == resource_id,
                *self._compatible_embedding_filters(),
            )
            .order_by(
                ResourceEmbedding.updated_at.desc()
            )
            .limit(1)
        )

        embedding = db.execute(
            statement
        ).scalars().first()

        if embedding is None:
            raise ResourceEmbeddingNotFoundError(
                "No compatible ready embedding exists "
                "for the requested resource."
            )

        if embedding.embedding is None:
            raise ResourceEmbeddingNotFoundError(
                "The resource embedding has no stored vector."
            )

        return embedding

    # ---------------------------------------------------------
    # Resource-to-resource comparison
    # ---------------------------------------------------------

    def compare_resources(
        self,
        db: Session,
        source_resource_id: UUID,
        target_resource_id: UUID,
    ) -> ResourceComparisonResult:
        """
        Compare two resources using their stored embeddings.

        Both resources must have compatible ready embeddings.
        """

        if source_resource_id == target_resource_id:
            raise ResourceSimilarityValidationError(
                "Source and target resources must be different."
            )

        source_embedding = self.get_resource_embedding(
            db,
            source_resource_id,
        )

        target_embedding = self.get_resource_embedding(
            db,
            target_resource_id,
        )

        distance = float(
            db.query(
                ResourceEmbedding.embedding.cosine_distance(
                    list(source_embedding.embedding)
                )
            )
            .filter(
                ResourceEmbedding.id == target_embedding.id
            )
            .scalar()
        )

        similarity = self.distance_to_similarity(
            distance
        )

        return ResourceComparisonResult(
            source_resource_id=source_resource_id,
            target_resource_id=target_resource_id,
            cosine_distance=distance,
            similarity_score=similarity,
        )

    # ---------------------------------------------------------
    # Find resources similar to another resource
    # ---------------------------------------------------------

    def find_similar_to_resource(
        self,
        db: Session,
        resource_id: UUID,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> list[ResourceSimilarityResult]:
        """
        Retrieve nearest neighbors of an existing resource.
        """

        source_embedding = self.get_resource_embedding(
            db,
            resource_id,
        )

        return self.find_similar_resources(
            db=db,
            query_vector=list(source_embedding.embedding),
            limit=limit,
            min_similarity=min_similarity,
            exclude_resource_id=resource_id,
        )