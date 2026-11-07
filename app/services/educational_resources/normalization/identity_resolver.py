from __future__ import annotations

import re
from typing import Any

from app.schemas.external_resources import ExternalResource

from app.services.educational_resources.normalization.url_normalizer import (
    ResourceURLNormalizer,
)


class ResourceIdentityResolver:
    """Resolve strong identities for external resources."""

    DOI_PATTERN = re.compile(
        r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
        re.IGNORECASE,
    )

    DOI_URL_PREFIXES = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
    )

    @staticmethod
    def _resource_type_key(resource: ExternalResource) -> str:
        value = resource.resource_type

        if hasattr(value, "value"):
            value = value.value

        return str(value).casefold()

    @classmethod
    def _normalize_doi(cls, value: str) -> str | None:
        candidate = value.strip()

        lowered = candidate.lower()

        for prefix in cls.DOI_URL_PREFIXES:
            if lowered.startswith(prefix):
                candidate = candidate[len(prefix):]
                break

        candidate = candidate.strip().rstrip(".,;")

        match = cls.DOI_PATTERN.search(candidate)

        if not match:
            return None

        return match.group(0).rstrip(".,;").casefold()

    @classmethod
    def _extract_dois(cls, value: Any) -> set[str]:
        dois: set[str] = set()

        if isinstance(value, str):
            normalized = cls._normalize_doi(value)

            if normalized:
                dois.add(normalized)

            return dois

        if isinstance(value, dict):
            for key, item in value.items():
                key_normalized = str(key).casefold()

                if key_normalized in {
                    "doi",
                    "doi_url",
                    "digital_object_identifier",
                }:
                    if isinstance(item, str):
                        normalized = cls._normalize_doi(item)

                        if normalized:
                            dois.add(normalized)

                dois.update(cls._extract_dois(item))

        elif isinstance(value, (list, tuple, set)):
            for item in value:
                dois.update(cls._extract_dois(item))

        return dois

    def resolve(
        self,
        resource: ExternalResource,
    ) -> frozenset[str]:
        if not isinstance(resource, ExternalResource):
            raise TypeError(
                "Expected an ExternalResource instance."
            )

        resource_type = self._resource_type_key(resource)

        identities: set[str] = set()

        provider = resource.provider.strip().casefold()
        external_id = resource.external_id.strip()

        if provider and external_id:
            identities.add(
                f"type:{resource_type}:provider:{provider}:{external_id}"
            )

        for doi in self._extract_dois(resource.metadata):
            identities.add(
                f"type:{resource_type}:doi:{doi}"
            )

        if resource.canonical_url:
            normalized_url = ResourceURLNormalizer.normalize(
                resource.canonical_url
            )

            if normalized_url:
                identities.add(
                    f"type:{resource_type}:url:{normalized_url}"
                )

        return frozenset(identities)