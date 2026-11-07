from __future__ import annotations

from dataclasses import dataclass

from typing import Any

from app.schemas.resource_metadata import (
    ResourceClassification,
)

from app.services.recommendations.content_based.feature_normalizer import (
    ContentFeatureNormalizer,
)


@dataclass(frozen=True, slots=True)
class ExtractedContentFeatures:
    """
    Immutable normalized representation of resource features.

    This structure is an intermediate feature-extraction
    result. It is not yet the final resource representation
    used for similarity computation.
    """

    resource_id: str

    title: str

    description: str

    subject: str

    resource_type: str

    category_slugs: tuple[str, ...]

    topics: tuple[str, ...]

    keywords: tuple[str, ...]

    learning_objectives: tuple[str, ...]

    prerequisites: tuple[str, ...]

    content_format: str

    language: str

    difficulty: str

    tokens: tuple[str, ...]

    @property
    def has_content_features(self) -> bool:
        """
        Return whether the resource contains at least one
        meaningful textual content feature.
        """

        return bool(
            self.title
            or self.description
            or self.subject
            or self.category_slugs
            or self.topics
            or self.keywords
            or self.learning_objectives
            or self.prerequisites
        )

    @property
    def feature_count(self) -> int:
        """
        Count populated feature groups.

        This counts groups, not individual terms.
        """

        groups = (
            self.title,
            self.description,
            self.subject,
            self.resource_type,
            self.category_slugs,
            self.topics,
            self.keywords,
            self.learning_objectives,
            self.prerequisites,
            self.content_format,
            self.language,
            self.difficulty,
        )

        return sum(bool(group) for group in groups)


class ContentFeatureExtractor:
    """
    Extracts normalized content features from an existing
    ResourceClassification instance.

    The extractor also supports compatible mapping/object
    inputs to allow future integration with resource providers.

    It does not access the database or call external APIs.
    """

    def __init__(
        self,
        normalizer: ContentFeatureNormalizer | None = None,
    ) -> None:

        self.normalizer = (
            normalizer
            or ContentFeatureNormalizer()
        )

    @staticmethod
    def _get_value(
        resource: Any,
        field: str,
        default: Any = None,
    ) -> Any:
        """
        Read a field from a Pydantic model, mapping or
        compatible resource object.
        """

        if isinstance(resource, dict):
            return resource.get(field, default)

        return getattr(
            resource,
            field,
            default,
        )

    def _normalize_optional_text(
        self,
        value: Any,
    ) -> str:
        if value is None:
            return ""

        if not isinstance(value, str):
            raise TypeError(
                "Optional content fields must be strings."
            )

        return self.normalizer.normalize_text(value)

    def _normalize_required_text(
        self,
        value: Any,
        field_name: str,
    ) -> str:

        normalized = self._normalize_optional_text(value)

        if not normalized:
            raise ValueError(
                f"Resource field '{field_name}' cannot be empty."
            )

        return normalized

    def _normalize_list(
        self,
        value: Any,
        field_name: str,
    ) -> tuple[str, ...]:

        if value is None:
            return ()

        try:
            return self.normalizer.normalize_terms(value)

        except (TypeError, ValueError) as exc:

            raise ValueError(
                f"Invalid resource feature '{field_name}': {exc}"
            ) from exc

    def extract(
        self,
        resource: ResourceClassification,
    ) -> ExtractedContentFeatures:
        """
        Extract normalized features from a resource.

        Required:
        - resource_id
        - title
        - resource_type

        Optional:
        - description
        - subject
        - categories
        - topics
        - keywords
        - learning objectives
        - prerequisites
        - content format
        - language
        - difficulty

        Missing optional values remain empty.
        """

        if not isinstance(
            resource,
            ResourceClassification,
        ) and not isinstance(resource, dict):

            raise TypeError(
                "Expected ResourceClassification or a mapping."
            )

        resource_id = self._normalize_required_text(
            self._get_value(resource, "resource_id"),
            "resource_id",
        )

        title = self._normalize_required_text(
            self._get_value(resource, "title"),
            "title",
        )

        resource_type = self._normalize_required_text(
            self._get_value(resource, "resource_type"),
            "resource_type",
        )

        description = self._normalize_optional_text(
            self._get_value(resource, "description")
        )

        subject = self._normalize_optional_text(
            self._get_value(resource, "subject")
        )

        category_slugs = self._normalize_list(
            self._get_value(resource, "category_slugs"),
            "category_slugs",
        )

        topics = self._normalize_list(
            self._get_value(resource, "topics"),
            "topics",
        )

        keywords = self._normalize_list(
            self._get_value(resource, "keywords"),
            "keywords",
        )

        learning_objectives = self._normalize_list(
            self._get_value(resource, "learning_objectives"),
            "learning_objectives",
        )

        prerequisites = self._normalize_list(
            self._get_value(resource, "prerequisites"),
            "prerequisites",
        )

        content_format = self._normalize_optional_text(
            self._get_value(resource, "content_format")
        )

        language = self._normalize_optional_text(
            self._get_value(resource, "language")
        )

        difficulty = self._normalize_optional_text(
            self._get_value(resource, "difficulty")
        )

        textual_features = (
            title,
            description,
            subject,
            *category_slugs,
            *topics,
            *keywords,
            *learning_objectives,
            *prerequisites,
        )

        tokens = self.normalizer.tokenize(
            textual_features
        )

        return ExtractedContentFeatures(
            resource_id=resource_id,
            title=title,
            description=description,
            subject=subject,
            resource_type=resource_type,
            category_slugs=category_slugs,
            topics=topics,
            keywords=keywords,
            learning_objectives=learning_objectives,
            prerequisites=prerequisites,
            content_format=content_format,
            language=language,
            difficulty=difficulty,
            tokens=tokens,
        )