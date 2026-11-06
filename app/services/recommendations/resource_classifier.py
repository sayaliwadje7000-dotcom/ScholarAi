from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.schemas.resource_metadata import (
    ResourceClassification,
    ResourceMetadata,
)


class ResourceClassifier:
    """
    Deterministic classifier for existing educational resources.

    Classification uses explicit database fields, category relationships,
    and standardized metadata.

    It does not infer missing subjects, topics, prerequisites,
    difficulty levels, or learning objectives.
    """

    @staticmethod
    def _get_value(resource: Any, field: str, default=None):
        return getattr(resource, field, default)

    @staticmethod
    def _get_metadata(resource: Any) -> ResourceMetadata:
        raw_metadata = getattr(resource, "metadata", None)

        # SQLAlchemy model maps the database metadata column to
        # recommendation_metadata in the existing implementation.
        if raw_metadata is None:
            raw_metadata = getattr(
                resource,
                "recommendation_metadata",
                None,
            )

        if raw_metadata is None:
            raw_metadata = {}

        if not isinstance(raw_metadata, Mapping):
            raise ValueError(
                "Resource metadata must be a dictionary-like object."
            )

        try:
            return ResourceMetadata.model_validate(dict(raw_metadata))
        except ValidationError as exc:
            raise ValueError(
                "Resource contains invalid standardized metadata."
            ) from exc

    @staticmethod
    def _get_category_slugs(resource: Any) -> list[str]:
        categories = getattr(resource, "categories", None) or []

        slugs = []

        for category in categories:
            slug = getattr(category, "slug", None)

            if isinstance(slug, str):
                slug = slug.strip().lower().replace(" ", "-")

                if slug:
                    slugs.append(slug)

        return ResourceMetadata(
            topics=slugs
        ).topics

    def classify(self, resource: Any) -> ResourceClassification:
        """
        Convert a StudyResource-like object into a normalized
        ResourceClassification.
        """

        resource_id = self._get_value(resource, "id")
        title = self._get_value(resource, "title")
        resource_type = self._get_value(resource, "resource_type")

        if resource_id is None:
            raise ValueError("Resource ID is required.")

        if not isinstance(title, str) or not title.strip():
            raise ValueError("Resource title is required.")

        if not isinstance(resource_type, str) or not resource_type.strip():
            raise ValueError("Resource type is required.")

        metadata = self._get_metadata(resource)

        subject = self._get_value(resource, "subject")
        difficulty = self._get_value(resource, "difficulty")
        language = self._get_value(resource, "language")

        quality_score = self._get_value(resource, "quality_score")

        estimated_duration = self._get_value(
            resource,
            "estimated_duration_minutes",
        )

        published_at = self._get_value(resource, "published_at")

        if quality_score is not None:
            quality_score = float(quality_score)

        return ResourceClassification(
            resource_id=str(resource_id),
            title=title.strip(),
            resource_type=resource_type.strip().lower(),
            subject=subject,
            difficulty=(
                difficulty.strip().lower()
                if isinstance(difficulty, str)
                else difficulty
            ),
            language=(
                language.strip().lower()
                if isinstance(language, str)
                else language
            ),
            category_slugs=self._get_category_slugs(resource),
            topics=metadata.topics,
            keywords=metadata.keywords,
            learning_objectives=metadata.learning_objectives,
            prerequisites=metadata.prerequisites,
            content_format=metadata.content_format,
            estimated_duration_minutes=estimated_duration,
            estimated_reading_minutes=metadata.estimated_reading_minutes,
            is_beginner_friendly=metadata.is_beginner_friendly,
            quality_score=quality_score,
            published_at=published_at,
            last_verified_at=metadata.last_verified_at,
            is_active=resource.is_active,
        )  