from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from app.schemas.external_resources import ExternalResource

from app.services.educational_resources.normalization.text_normalizer import (
    ResourceTextNormalizer,
)
from app.services.educational_resources.normalization.url_normalizer import (
    ResourceURLNormalizer,
)


class ResourceNormalizationError(ValueError):
    """Raised when an external resource cannot be normalized."""


class ExternalResourceNormalizer:
    """Normalize external educational resource objects."""

    def __init__(
        self,
        text_normalizer: ResourceTextNormalizer | None = None,
        url_normalizer: type[ResourceURLNormalizer] | None = None,
    ) -> None:
        self.text_normalizer = (
            text_normalizer or ResourceTextNormalizer()
        )
        self.url_normalizer = url_normalizer or ResourceURLNormalizer

    @classmethod
    def _normalize_metadata(cls, value: Any) -> Any:
        if isinstance(value, str):
            return ResourceTextNormalizer.normalize(value)

        if isinstance(value, list):
            return [
                cls._normalize_metadata(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return tuple(
                cls._normalize_metadata(item)
                for item in value
            )

        if isinstance(value, dict):
            normalized = {}

            for key, item in value.items():
                normalized_key = (
                    ResourceTextNormalizer.normalize(str(key))
                )

                if normalized_key is not None:
                    normalized[normalized_key] = (
                        cls._normalize_metadata(item)
                    )

            return normalized

        return value

    @staticmethod
    def _normalize_datetime(
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None

        if not isinstance(value, datetime):
            raise ResourceNormalizationError(
                "Resource dates must be datetime objects."
            )

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    def normalize(
        self,
        resource: ExternalResource,
    ) -> ExternalResource:
        if not isinstance(resource, ExternalResource):
            raise TypeError(
                "Expected an ExternalResource instance."
            )

        try:
            provider = self.text_normalizer.normalize(
                resource.provider
            )

            external_id = self.text_normalizer.normalize(
                resource.external_id
            )

            title = self.text_normalizer.normalize(
                resource.title
            )

            canonical_url = self.url_normalizer.normalize(
                resource.canonical_url
            )

            description = self.text_normalizer.normalize(
                resource.description
            )

            authors = self.text_normalizer.normalize_authors(
                resource.authors
            )

            subject = self.text_normalizer.normalize(
                resource.subject
            )

            language = self.text_normalizer.normalize(
                resource.language
            )

            license_value = self.text_normalizer.normalize(
                resource.license
            )

            metadata = self._normalize_metadata(
                resource.metadata
            )

            return replace(
                resource,
                provider=provider,
                external_id=external_id,
                title=title,
                canonical_url=canonical_url,
                description=description,
                authors=authors,
                subject=subject,
                language=(
                    language.casefold()
                    if language is not None
                    else None
                ),
                license=license_value,
                published_at=self._normalize_datetime(
                    resource.published_at
                ),
                retrieved_at=self._normalize_datetime(
                    resource.retrieved_at
                ),
                metadata=metadata,
            )

        except (TypeError, ValueError):
            raise

        except Exception as exc:
            raise ResourceNormalizationError(
                "Failed to normalize external resource."
            ) from exc