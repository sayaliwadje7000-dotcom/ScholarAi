from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID

from app.services.recommendations.content_based.candidate_models import (
    ContentBasedCandidate,
)


class ContentFilteringError(ValueError):
    """Raised when content-based filtering inputs are invalid."""


@dataclass(frozen=True, slots=True)
class ContentFilterCriteria:

    resource_types: frozenset[str] = field(
        default_factory=frozenset
    )

    subjects: frozenset[str] = field(
        default_factory=frozenset
    )

    languages: frozenset[str] = field(
        default_factory=frozenset
    )

    difficulty_levels: frozenset[str] = field(
        default_factory=frozenset
    )

    categories: frozenset[str] = field(
        default_factory=frozenset
    )

    excluded_resource_ids: frozenset[UUID] = field(
        default_factory=frozenset
    )

    minimum_score: float = 0.0

    minimum_confidence: float = 0.0

    exclude_inactive: bool = True

    def __post_init__(self):

        collection_fields = (
            "resource_types",
            "subjects",
            "languages",
            "difficulty_levels",
            "categories",
        )

        for field_name in collection_fields:

            values = getattr(self, field_name)

            if isinstance(values, str):
                values = (values,)

            try:
                normalized = frozenset(
                    value.strip().casefold()
                    for value in values
                    if isinstance(value, str) and value.strip()
                )
            except TypeError:

                raise ContentFilteringError(
                    f"{field_name} must be an iterable of strings."
                ) from None

            object.__setattr__(
                self,
                field_name,
                normalized,
            )

        if isinstance(self.excluded_resource_ids, (str, bytes)):
            raise ContentFilteringError(
                "excluded_resource_ids must contain UUID values."
            )

        try:
            excluded_ids = frozenset(
                UUID(str(resource_id))
                for resource_id in self.excluded_resource_ids
            )
        except (TypeError, ValueError, AttributeError):

            raise ContentFilteringError(
                "Invalid excluded resource ID."
            ) from None

        object.__setattr__(
            self,
            "excluded_resource_ids",
            excluded_ids,
        )

        self._validate_threshold(
            self.minimum_score,
            "minimum_score",
        )

        self._validate_threshold(
            self.minimum_confidence,
            "minimum_confidence",
        )

        if not isinstance(self.exclude_inactive, bool):

            raise ContentFilteringError(
                "exclude_inactive must be a boolean."
            )

    @staticmethod
    def _validate_threshold(value, name):

        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise ContentFilteringError(
                f"{name} must be numeric."
            )

        if not 0.0 <= value <= 1.0:

            raise ContentFilteringError(
                f"{name} must be between 0 and 1."
            )

        import math

        if not math.isfinite(value):

            raise ContentFilteringError(
                f"{name} must be finite."
            )


class ContentBasedFilteringService:
    """
    Deterministic filtering for content-based recommendation candidates.

    Filtering never modifies the original scoring result.
    """

    @staticmethod
    def _normalize(value):

        if value is None:
            return ""

        return str(
            getattr(value, "value", value)
        ).strip().casefold()

    @staticmethod
    def _matches_collection(
        actual_value,
        allowed_values,
    ):

        if not allowed_values:
            return True

        actual = ContentBasedFilteringService._normalize(
            actual_value
        )

        return bool(actual) and actual in allowed_values

    def matches(
        self,
        candidate: ContentBasedCandidate,
        criteria: ContentFilterCriteria,
    ) -> bool:

        if not isinstance(candidate, ContentBasedCandidate):

            raise TypeError(
                "Expected ContentBasedCandidate."
            )

        if not isinstance(criteria, ContentFilterCriteria):

            raise TypeError(
                "Expected ContentFilterCriteria."
            )

        features = candidate.features

        if criteria.exclude_inactive and not candidate.is_active:
            return False

        if candidate.resource_id in criteria.excluded_resource_ids:
            return False

        if candidate.score < criteria.minimum_score:
            return False

        if candidate.confidence < criteria.minimum_confidence:
            return False

        if not self._matches_collection(
            features.resource_type,
            criteria.resource_types,
        ):
            return False

        if not self._matches_collection(
            features.subject,
            criteria.subjects,
        ):
            return False

        if not self._matches_collection(
            features.language,
            criteria.languages,
        ):
            return False

        if not self._matches_collection(
            features.difficulty,
            criteria.difficulty_levels,
        ):
            return False

        if criteria.categories:

            candidate_categories = {
                self._normalize(category)
                for category in features.category_slugs
            }

            if not candidate_categories.intersection(
                criteria.categories
            ):
                return False

        return True

    def filter(
        self,
        candidates: Iterable[ContentBasedCandidate],
        criteria: ContentFilterCriteria | None = None,
    ) -> list[ContentBasedCandidate]:

        if criteria is None:
            criteria = ContentFilterCriteria()

        if not isinstance(criteria, ContentFilterCriteria):

            raise TypeError(
                "Expected ContentFilterCriteria."
            )

        if isinstance(candidates, (str, bytes)):

            raise TypeError(
                "Candidates must be an iterable of candidates."
            )

        try:
            iterator = iter(candidates)
        except TypeError:

            raise TypeError(
                "Candidates must be iterable."
            ) from None

        filtered = []

        for candidate in iterator:

            if not isinstance(candidate, ContentBasedCandidate):

                raise TypeError(
                    "Every item must be ContentBasedCandidate."
                )

            if self.matches(candidate, criteria):

                filtered.append(candidate)

        return filtered