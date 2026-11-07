from __future__ import annotations

import inspect

from collections.abc import Iterable
from uuid import UUID

from app.schemas.recommendations import (
    RecommendationRequest,
)

from app.services.recommendations.context_builder import (
    LearningContextBuilder,
)

from app.services.recommendations.content_based.query_context import (
    ContentQueryContext,
    ContentQueryFilters,
    QueryContextValidationError,
)


class ContentQueryContextError(Exception):
    """Base exception for query-context operations."""


class EmptyLearningIntentError(ContentQueryContextError):
    """Raised when no usable learning intent exists."""


class QueryEmbeddingError(ContentQueryContextError):
    """Raised when query embedding generation fails."""


class ContentQueryContextService:
    """
    Builds a query-aware content recommendation context.

    Responsibilities:
    - Build the user's learning context.
    - Construct a meaningful semantic query.
    - Generate a query embedding.
    - Resolve effective search filters.
    """

    DEFAULT_DIMENSIONS = 1536

    def __init__(
        self,
        embedding_service,
        context_builder=None,
        expected_dimensions=DEFAULT_DIMENSIONS,
    ):

        if embedding_service is None:

            raise TypeError(
                "embedding_service is required."
            )

        if (
            isinstance(expected_dimensions, bool)
            or not isinstance(expected_dimensions, int)
            or expected_dimensions <= 0
        ):

            raise ValueError(
                "expected_dimensions must be a positive integer."
            )

        self.embedding_service = embedding_service

        self.context_builder = (
            context_builder
            or LearningContextBuilder()
        )

        self.expected_dimensions = expected_dimensions

    @staticmethod
    def _normalize_text(value):

        if value is None:
            return ""

        if not isinstance(value, str):
            return ""

        return " ".join(value.split())

    @staticmethod
    def _unique(values: Iterable[str]):

        result = []

        seen = set()

        for value in values:

            normalized = (
                ContentQueryContextService._normalize_text(
                    value
                )
            )

            if not normalized:
                continue

            key = normalized.casefold()

            if key not in seen:

                seen.add(key)

                result.append(normalized)

        return result

    def build_query_text(
        self,
        request: RecommendationRequest,
        learning_context,
    ) -> str:

        if not isinstance(
            request,
            RecommendationRequest,
        ):

            raise TypeError(
                "Expected RecommendationRequest."
            )

        query_parts = []

        explicit_query = self._normalize_text(
            request.query
        )

        if explicit_query:
            query_parts.append(explicit_query)

        subject = self._normalize_text(
            request.subject
        )

        if subject:
            query_parts.append(
                f"Subject: {subject}"
            )

        learning_goals = self._unique(
            learning_context.learning_goals
        )

        if learning_goals:

            query_parts.append(
                "Learning goals: "
                + ", ".join(learning_goals)
            )

        preferred_subjects = self._unique(
            learning_context.preferred_subjects
        )

        if preferred_subjects:

            query_parts.append(
                "Preferred subjects: "
                + ", ".join(preferred_subjects)
            )

        query_text = "\n".join(
            self._unique(query_parts)
        )

        if not query_text:

            raise EmptyLearningIntentError(
                "No query, subject, learning goal or preferred subject "
                "is available to generate a content-based recommendation."
            )

        return query_text

    def build_filters(
        self,
        request: RecommendationRequest,
        learning_context,
    ) -> ContentQueryFilters:

        resource_types = tuple(
            resource_type.value
            if hasattr(resource_type, "value")
            else str(resource_type)
            for resource_type in (
                request.resource_types or []
            )
        )

        language = (
            request.language
            or learning_context.preferred_language
        )

        return ContentQueryFilters(
            subject=request.subject,
            language=language,
            difficulty_level=(
                request.difficulty_level.value
                if request.difficulty_level is not None
                and hasattr(request.difficulty_level, "value")
                else (
                    str(request.difficulty_level)
                    if request.difficulty_level is not None
                    else None
                )
            ),
            resource_types=resource_types,
            preferred_subjects=tuple(
                learning_context.preferred_subjects
            ),
            learning_goals=tuple(
                learning_context.learning_goals
            ),
            exclude_completed=request.exclude_completed,
        )

    async def _embed_query(self, query_text):

        try:

            result = self.embedding_service.embed_query(
                query_text
            )

            if inspect.isawaitable(result):
                result = await result

        except Exception as exc:

            raise QueryEmbeddingError(
                "Unable to generate the query embedding."
            ) from exc

        if result is None:

            raise QueryEmbeddingError(
                "Embedding provider returned no result."
            )

        vector = getattr(
            result,
            "vector",
            None,
        )

        if vector is None:

            raise QueryEmbeddingError(
                "Embedding result does not contain a vector."
            )

        dimensions = getattr(
            result,
            "dimensions",
            None,
        )

        provider = getattr(
            result,
            "provider",
            None,
        )

        model = getattr(
            result,
            "model",
            None,
        )

        if dimensions != self.expected_dimensions:

            raise QueryEmbeddingError(
                "Query embedding dimensions do not match configuration."
            )

        if len(vector) != self.expected_dimensions:

            raise QueryEmbeddingError(
                "Query embedding vector has an invalid length."
            )

        if not provider or not model:

            raise QueryEmbeddingError(
                "Embedding provider and model metadata are required."
            )

        return (
            tuple(float(value) for value in vector),
            provider,
            model,
            dimensions,
        )

    async def build(
        self,
        user,
        request: RecommendationRequest,
        interactions=(),
    ) -> ContentQueryContext:

        if user is None:

            raise TypeError(
                "An authenticated user object is required."
            )

        if not isinstance(
            request,
            RecommendationRequest,
        ):

            raise TypeError(
                "Expected RecommendationRequest."
            )

        user_id = getattr(
            user,
            "id",
            None,
        )

        if not isinstance(user_id, UUID):

            raise TypeError(
                "User must have a valid UUID id."
            )

        try:

            learning_context = self.context_builder.build(
                user=user,
                preferences=getattr(
                    user,
                    "preferences",
                    None,
                ),
                request=request,
                interactions=interactions,
            )

            query_text = self.build_query_text(
                request,
                learning_context,
            )

            filters = self.build_filters(
                request,
                learning_context,
            )

            (
                query_embedding,
                provider,
                model,
                dimensions,
            ) = await self._embed_query(
                query_text
            )

            return ContentQueryContext(
                user_id=user_id,
                query_text=query_text,
                query_embedding=query_embedding,
                learning_context=learning_context,
                filters=filters,
                embedding_provider=provider,
                embedding_model=model,
                embedding_dimensions=dimensions,
            )

        except (
            EmptyLearningIntentError,
            QueryEmbeddingError,
            QueryContextValidationError,
        ):

            raise

        except Exception as exc:

            raise ContentQueryContextError(
                "Failed to construct content recommendation context."
            ) from exc