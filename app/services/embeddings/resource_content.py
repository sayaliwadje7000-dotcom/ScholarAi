from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.services.embeddings.metadata import compute_content_hash


@dataclass(frozen=True, slots=True)
class ResourceContent:
    resource_id: UUID
    text: str
    content_hash: str


class ResourceContentBuilder:
    """
    Converts a StudyResource into deterministic semantic text.

    The representation includes descriptive and educational
    metadata rather than only the resource title.
    """

    VERSION = "1.0.0"

    @staticmethod
    def _clean(value: object) -> str:
        if value is None:
            return ""

        if not isinstance(value, str):
            return ""

        return " ".join(value.split()).strip()

    @classmethod
    def _clean_list(cls, value: object) -> list[str]:
        if value is None:
            return []

        if isinstance(value, str):
            value = [value]

        if not isinstance(value, (list, tuple, set)):
            return []

        result = []
        seen = set()

        for item in value:
            normalized = cls._clean(item)

            if not normalized:
                continue

            key = normalized.casefold()

            if key not in seen:
                seen.add(key)
                result.append(normalized)

        return result

    @staticmethod
    def _get_categories(resource) -> list[str]:
        categories = getattr(resource, "categories", None) or []

        slugs = []

        for category in categories:
            slug = getattr(category, "slug", None)

            if isinstance(slug, str) and slug.strip():
                slugs.append(slug.strip())

        return slugs

    def build(self, resource) -> ResourceContent:
        resource_id = getattr(resource, "id", None)

        if not isinstance(resource_id, UUID):
            raise TypeError(
                "Resource must have a valid UUID id."
            )

        title = self._clean(
            getattr(resource, "title", None)
        )

        if not title:
            raise ValueError(
                "Resource title cannot be empty."
            )

        description = self._clean(
            getattr(resource, "description", None)
        )

        subject = self._clean(
            getattr(resource, "subject", None)
        )

        resource_type = self._clean(
            getattr(resource, "resource_type", None)
        )

        provider = self._clean(
            getattr(resource, "provider", None)
        )

        language = self._clean(
            getattr(resource, "language", None)
        )

        difficulty = self._clean(
            getattr(resource, "difficulty_level", None)
        )

        metadata = getattr(
            resource,
            "resource_metadata",
            {},
        ) or {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "Resource metadata must be a dictionary."
            )

        topics = self._clean_list(
            metadata.get("topics")
        )

        keywords = self._clean_list(
            metadata.get("keywords")
        )

        objectives = self._clean_list(
            metadata.get("learning_objectives")
        )

        prerequisites = self._clean_list(
            metadata.get("prerequisites")
        )

        content_format = self._clean(
            metadata.get("content_format")
        )

        categories = self._clean_list(
            self._get_categories(resource)
        )

        sections = [
            ("Title", title),
            ("Description", description),
            ("Subject", subject),
            ("Resource Type", resource_type),
            ("Provider", provider),
            ("Language", language),
            ("Difficulty", difficulty),
            ("Categories", ", ".join(categories)),
            ("Topics", ", ".join(topics)),
            ("Keywords", ", ".join(keywords)),
            ("Learning Objectives", ", ".join(objectives)),
            ("Prerequisites", ", ".join(prerequisites)),
            ("Content Format", content_format),
        ]

        representation = "\n".join(
            f"{label}: {value}"
            for label, value in sections
            if value
        )

        if not representation.strip():
            raise ValueError(
                "Resource has no usable semantic content."
            )

        content_hash = compute_content_hash(
            f"{self.VERSION}\n{representation}"
        )

        return ResourceContent(
            resource_id=resource_id,
            text=representation,
            content_hash=content_hash,
        )