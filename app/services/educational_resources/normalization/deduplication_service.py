from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any

from app.schemas.external_resources import ExternalResource

from app.services.educational_resources.normalization.identity_resolver import (
    ResourceIdentityResolver,
)
from app.services.educational_resources.normalization.resource_normalizer import (
    ExternalResourceNormalizer,
)


class ResourceDeduplicationService:
    """Deduplicate and merge external educational resources."""

    def __init__(
        self,
        normalizer: ExternalResourceNormalizer | None = None,
        identity_resolver: ResourceIdentityResolver | None = None,
    ) -> None:
        self.normalizer = normalizer or ExternalResourceNormalizer()
        self.identity_resolver = (
            identity_resolver or ResourceIdentityResolver()
        )

    @staticmethod
    def _resource_type(resource: ExternalResource) -> str:
        value = resource.resource_type

        if hasattr(value, "value"):
            value = value.value

        return str(value).casefold()

    @classmethod
    def _quality_key(
        cls,
        resource: ExternalResource,
    ) -> tuple:
        """Prefer resources containing richer metadata."""

        completeness = sum(
            value is not None and value != ""
            for value in (
                resource.description,
                resource.subject,
                resource.language,
                resource.license,
                resource.published_at,
                resource.canonical_url,
            )
        )

        completeness += len(resource.authors)
        completeness += len(resource.metadata)

        return (
            -completeness,
            resource.provider.casefold(),
            resource.external_id.casefold(),
            resource.canonical_url or "",
        )

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return value is None or value == "" or value == [] or value == {}

    @classmethod
    def _merge_metadata(
        cls,
        resources: list[ExternalResource],
    ) -> dict[str, Any]:
        """
        Merge metadata from duplicate resources.

        Existing source_provenance entries are preserved.
        New provenance entries are added without duplicates.
        Both dictionary and list provenance formats are supported.
        """

        merged: dict[str, Any] = {}
        provenance: list[dict[str, Any]] = []

        def add_provenance(value: Any) -> None:
            """Add existing provenance entries without duplication."""

            if isinstance(value, dict):
                entries = [value]

            elif isinstance(value, (list, tuple)):
                entries = value

            else:
                return

            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                entry_copy = dict(entry)

                if entry_copy not in provenance:
                    provenance.append(entry_copy)

        # First preserve and merge metadata from every resource.
        for resource in resources:
            metadata = resource.metadata or {}

            if not isinstance(metadata, dict):
                continue

            for key, value in metadata.items():

                # Handle provenance separately so it is never overwritten.
                if key == "source_provenance":
                    add_provenance(value)
                    continue

                if key not in merged or cls._is_empty(merged[key]):
                    if not cls._is_empty(value):
                        merged[key] = value

        # Add provenance generated from each resource.
        for resource in resources:
            entry: dict[str, Any] = {
                "provider": resource.provider,
                "external_id": resource.external_id,
            }

            if resource.canonical_url:
                entry["canonical_url"] = resource.canonical_url

            add_provenance(entry)

        # Keep provenance ordering deterministic.
        provenance.sort(
            key=lambda item: (
                str(item.get("provider", "")).casefold(),
                str(item.get("external_id", "")).casefold(),
                str(item.get("canonical_url", "")),
                repr(sorted(item.items())),
            )
        )

        if provenance:
            merged["source_provenance"] = provenance

        return merged

    @staticmethod
    def _merge_authors(
        resources: list[ExternalResource],
    ) -> tuple[str, ...]:
        authors: dict[str, str] = {}

        for resource in resources:
            for author in resource.authors:
                key = author.casefold().strip()

                if key and key not in authors:
                    authors[key] = author

        return tuple(
            authors[key]
            for key in sorted(authors)
        )

    @classmethod
    def _first_non_empty(
        cls,
        resources: list[ExternalResource],
        field_name: str,
    ) -> Any:
        for resource in resources:
            value = getattr(resource, field_name)

            if not cls._is_empty(value):
                return value

        return None

    def _merge_group(
        self,
        resources: list[ExternalResource],
    ) -> ExternalResource:
        ordered = sorted(
            resources,
            key=self._quality_key,
        )

        primary = ordered[0]

        merged_metadata = self._merge_metadata(ordered)

        return replace(
            primary,
            description=self._first_non_empty(
                ordered,
                "description",
            ),
            authors=self._merge_authors(ordered),
            subject=self._first_non_empty(
                ordered,
                "subject",
            ),
            language=self._first_non_empty(
                ordered,
                "language",
            ),
            published_at=self._first_non_empty(
                ordered,
                "published_at",
            ),
            license=self._first_non_empty(
                ordered,
                "license",
            ),
            metadata=merged_metadata,
        )

    def deduplicate(
        self,
        resources: list[ExternalResource],
    ) -> list[ExternalResource]:
        if not isinstance(resources, list):
            raise TypeError("Resources must be provided as a list.")

        if not resources:
            return []

        normalized_resources = [
            self.normalizer.normalize(resource)
            for resource in resources
        ]

        count = len(normalized_resources)

        parents = list(range(count))

        def find(index: int) -> int:
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]

            return index

        def union(first: int, second: int) -> None:
            root_first = find(first)
            root_second = find(second)

            if root_first != root_second:
                parents[root_second] = root_first

        identity_owner: dict[str, int] = {}

        for index, resource in enumerate(normalized_resources):
            identities = self.identity_resolver.resolve(resource)

            for identity in sorted(identities):
                existing_index = identity_owner.get(identity)

                if existing_index is None:
                    identity_owner[identity] = index
                else:
                    union(index, existing_index)

        groups: dict[int, list[ExternalResource]] = defaultdict(list)

        for index, resource in enumerate(normalized_resources):
            groups[find(index)].append(resource)

        results = [
            self._merge_group(group)
            for group in groups.values()
        ]

        results.sort(
            key=lambda resource: (
                self._resource_type(resource),
                resource.title.casefold(),
                resource.provider.casefold(),
                resource.external_id.casefold(),
                resource.canonical_url or "",
            )
        )

        return results