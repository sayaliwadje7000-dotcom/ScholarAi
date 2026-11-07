import json
import math

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.models.study_resource import StudyResource

from app.schemas.external_resources import (
    ExternalResource,
    ExternalResourceType,
)


class ResourceMappingError(Exception):
    """
    Raised when an external resource cannot be mapped
    into the internal StudyResource representation.
    """


class ExternalResourceMapper:
    """
    Converts normalized external provider resources
    into ScholarAI StudyResource objects.
    """

    SUPPORTED_RESOURCE_TYPES = {
        "video",
        "article",
        "course",
        "documentation",
        "tutorial",
        "website",
        "book",
    }

    MAX_TITLE_LENGTH = 255

    MAX_URL_LENGTH = 2048

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """
        Convert supported metadata values into JSON-safe
        representations.

        This prevents datetime, Enum, tuple and other
        non-JSON-native values from breaking JSONB storage.
        """

        if value is None:
            return None

        if isinstance(value, datetime):

            if value.tzinfo is None or value.utcoffset() is None:
                raise ResourceMappingError(
                    "Naive datetime values are not allowed "
                    "in resource metadata."
                )

            return value.astimezone(
                timezone.utc
            ).isoformat()

        if isinstance(value, Enum):
            return ExternalResourceMapper._json_safe(
                value.value
            )

        if isinstance(value, dict):

            normalized = {}

            for key, item in value.items():

                if not isinstance(key, str):
                    raise ResourceMappingError(
                        "Metadata dictionary keys must be strings."
                    )

                normalized[key] = (
                    ExternalResourceMapper._json_safe(item)
                )

            return normalized

        if isinstance(value, (list, tuple)):
            return [
                ExternalResourceMapper._json_safe(item)
                for item in value
            ]

        if isinstance(value, float):

            if not math.isfinite(value):
                raise ResourceMappingError(
                    "Metadata cannot contain NaN or infinity."
                )

            return value

        if isinstance(
            value,
            (str, int, bool),
        ):
            return value

        raise ResourceMappingError(
            f"Unsupported metadata value type: "
            f"{type(value).__name__}"
        )

    @classmethod
    def _validate_resource_type(
        cls,
        resource_type: ExternalResourceType,
    ) -> str:

        value = getattr(
            resource_type,
            "value",
            resource_type,
        )

        if value not in cls.SUPPORTED_RESOURCE_TYPES:

            raise ResourceMappingError(
                f"Unsupported resource type: {value}"
            )

        return value

    @classmethod
    def to_study_resource_values(
        cls,
        external_resource: ExternalResource,
    ) -> dict[str, Any]:
        """
        Convert an ExternalResource into keyword arguments
        accepted by the StudyResource SQLAlchemy model.

        This method does not write to the database.
        """

        if not isinstance(
            external_resource,
            ExternalResource,
        ):
            raise TypeError(
                "Expected an ExternalResource instance."
            )

        title = external_resource.title.strip()

        url = external_resource.canonical_url.strip()

        if not title:
            raise ResourceMappingError(
                "Resource title cannot be empty."
            )

        if len(title) > cls.MAX_TITLE_LENGTH:
            raise ResourceMappingError(
                "Resource title exceeds 255 characters."
            )

        if not url:
            raise ResourceMappingError(
                "Resource URL cannot be empty."
            )

        if len(url) > cls.MAX_URL_LENGTH:
            raise ResourceMappingError(
                "Resource URL exceeds 2048 characters."
            )

        resource_type = cls._validate_resource_type(
            external_resource.resource_type
        )

        provider_metadata = cls._json_safe(
            external_resource.metadata
        )

        provenance = {
            "provider": external_resource.provider,
            "external_id": external_resource.external_id,
            "canonical_url": url,
            "retrieved_at": external_resource.retrieved_at,
            "license": external_resource.license,
            "access_type": external_resource.access_type,
            "authors": list(external_resource.authors),
        }

        provenance = cls._json_safe(provenance)

        resource_metadata = {
            **provider_metadata,
            "external_source": provenance,
        }

        # Verify that the entire metadata structure can
        # be serialized before it reaches PostgreSQL.
        try:

            json.dumps(
                resource_metadata,
                allow_nan=False,
            )

        except (TypeError, ValueError) as exc:

            raise ResourceMappingError(
                "Resource metadata is not JSON serializable."
            ) from exc

        return {
            "title": title,
            "description": external_resource.description,
            "resource_type": resource_type,
            "url": url,
            "provider": external_resource.provider,
            "subject": external_resource.subject,
            "language": external_resource.language,
            "difficulty_level": None,
            "estimated_duration_minutes": None,
            "quality_score": None,
            "resource_metadata": resource_metadata,
            "is_active": True,
            "published_at": external_resource.published_at,
        }

    @classmethod
    def to_study_resource(
        cls,
        external_resource: ExternalResource,
    ) -> StudyResource:
        """
        Create an unsaved StudyResource instance.

        Database persistence and transaction management
        remain the responsibility of the calling service.
        """

        values = cls.to_study_resource_values(
            external_resource
        )

        return StudyResource(**values)