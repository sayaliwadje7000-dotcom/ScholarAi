from __future__ import annotations

import math

from dataclasses import dataclass
from uuid import UUID

from app.schemas.recommendations import LearningContext


class QueryContextValidationError(ValueError):
    """Raised when a content recommendation context is invalid."""


@dataclass(frozen=True, slots=True)
class ContentQueryFilters:

    subject: str | None = None
    language: str | None = None
    difficulty_level: str | None = None

    resource_types: tuple[str, ...] = ()
    preferred_subjects: tuple[str, ...] = ()
    learning_goals: tuple[str, ...] = ()

    exclude_completed: bool = True

    def __post_init__(self):

        # Validate and normalize optional string fields.
        for field_name in (
            "subject",
            "language",
            "difficulty_level",
        ):
            value = getattr(self, field_name)

            if value is not None:

                if not isinstance(value, str):
                    raise QueryContextValidationError(
                        f"{field_name} must be a string or None."
                    )

                normalized = value.strip()

                object.__setattr__(
                    self,
                    field_name,
                    normalized or None,
                )

        # Validate and normalize collection fields.
        for field_name in (
            "resource_types",
            "preferred_subjects",
            "learning_goals",
        ):
            values = getattr(self, field_name)

            if isinstance(values, str):
                values = (values,)

            if not isinstance(values, (tuple, list)):
                raise QueryContextValidationError(
                    f"{field_name} must be a list or tuple."
                )

            # Reject invalid values instead of silently ignoring them.
            if any(
                not isinstance(value, str)
                for value in values
            ):
                raise QueryContextValidationError(
                    f"Every {field_name} value must be a string."
                )

            normalized = tuple(
                dict.fromkeys(
                    value.strip()
                    for value in values
                    if value.strip()
                )
            )

            object.__setattr__(
                self,
                field_name,
                normalized,
            )

        # Validate completion filter.
        if not isinstance(self.exclude_completed, bool):
            raise QueryContextValidationError(
                "exclude_completed must be a boolean."
            )


@dataclass(frozen=True, slots=True)
class ContentQueryContext:

    user_id: UUID

    query_text: str

    query_embedding: tuple[float, ...]

    learning_context: LearningContext

    filters: ContentQueryFilters

    embedding_provider: str

    embedding_model: str

    embedding_dimensions: int

    def __post_init__(self):

        # Validate user identity.
        if not isinstance(self.user_id, UUID):
            raise QueryContextValidationError(
                "user_id must be a UUID."
            )

        # Validate query text.
        if not isinstance(self.query_text, str):
            raise QueryContextValidationError(
                "query_text must be a string."
            )

        if not self.query_text.strip():
            raise QueryContextValidationError(
                "query_text cannot be empty."
            )

        # Validate learning context.
        if not isinstance(
            self.learning_context,
            LearningContext,
        ):
            raise QueryContextValidationError(
                "learning_context must be LearningContext."
            )

        if self.learning_context.user_id != self.user_id:
            raise QueryContextValidationError(
                "Learning context belongs to a different user."
            )

        # Validate filters.
        if not isinstance(
            self.filters,
            ContentQueryFilters,
        ):
            raise QueryContextValidationError(
                "filters must be ContentQueryFilters."
            )

        # Validate embedding dimensions BEFORE comparing lengths.
        if (
            isinstance(self.embedding_dimensions, bool)
            or not isinstance(self.embedding_dimensions, int)
            or self.embedding_dimensions <= 0
        ):
            raise QueryContextValidationError(
                "Embedding dimensions must be a positive integer."
            )

        # Validate embedding vector.
        if not isinstance(self.query_embedding, (tuple, list)):
            raise QueryContextValidationError(
                "Query embedding must be a tuple or list."
            )

        if not self.query_embedding:
            raise QueryContextValidationError(
                "Query embedding cannot be empty."
            )

        if len(self.query_embedding) != self.embedding_dimensions:
            raise QueryContextValidationError(
                "Embedding dimensions do not match vector length."
            )

        for value in self.query_embedding:

            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise QueryContextValidationError(
                    "Embedding values must be numeric."
                )

            if not math.isfinite(value):
                raise QueryContextValidationError(
                    "Embedding values must be finite."
                )

        # Validate embedding provider.
        if (
            not isinstance(self.embedding_provider, str)
            or not self.embedding_provider.strip()
        ):
            raise QueryContextValidationError(
                "Embedding provider is required."
            )

        # Validate embedding model.
        if (
            not isinstance(self.embedding_model, str)
            or not self.embedding_model.strip()
        ):
            raise QueryContextValidationError(
                "Embedding model is required."
            )