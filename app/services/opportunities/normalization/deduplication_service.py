from copy import deepcopy
from typing import Any

from app.services.opportunities.normalization.identity_resolver import (
    OpportunityIdentityResolver,
)

from app.services.opportunities.normalization.opportunity_normalizer import (
    OpportunityNormalizer,
)


class OpportunityDeduplicationService:
    """
    Deduplicates normalized opportunities.

    Responsibilities:
    - Identify duplicate opportunities.
    - Merge compatible information.
    - Preserve source references.
    - Merge required skills.
    - Preserve eligibility conflicts.
    - Avoid overwriting known information.
    """

    MERGE_FIELDS = (
        "description",
        "organizer",
        "location",
        "registration_start",
        "registration_deadline",
        "event_start",
        "event_end",
        "application_url",
        "source_url",
        "published_at",
    )

    @staticmethod
    def _source_reference(opportunity: dict) -> dict:

        return {
            "provider": opportunity.get("provider"),
            "external_id": opportunity.get("external_id"),
            "official_url": opportunity.get("official_url"),
            "source_url": opportunity.get("source_url"),
            "application_url": opportunity.get("application_url"),
        }

    @staticmethod
    def _merge_list(first: list, second: list) -> list:

        merged = deepcopy(first)

        seen = {
            str(item).casefold()
            for item in merged
        }

        for item in second:

            key = str(item).casefold()

            if key not in seen:

                seen.add(key)

                merged.append(deepcopy(item))

        return merged

    @staticmethod
    def _merge_metadata(first: dict, second: dict) -> dict:

        merged = deepcopy(first)

        for key, value in second.items():

            if key == "sources":
                continue

            if key not in merged:

                merged[key] = deepcopy(value)

            elif merged[key] in (None, "", [], {}):

                merged[key] = deepcopy(value)

            elif merged[key] != value:

                conflicts = merged.setdefault(
                    "metadata_conflicts",
                    {},
                )

                conflict_values = conflicts.setdefault(
                    key,
                    [],
                )

                for candidate in (merged[key], value):

                    if candidate not in conflict_values:

                        conflict_values.append(
                            deepcopy(candidate)
                        )

        return merged

    @classmethod
    def _merge_eligibility(
        cls,
        first: dict,
        second: dict,
        metadata: dict,
    ) -> dict:

        merged = deepcopy(first)

        for key, value in second.items():

            if key not in merged:

                merged[key] = deepcopy(value)

            elif merged[key] != value:

                conflicts = metadata.setdefault(
                    "eligibility_conflicts",
                    {},
                )

                values = conflicts.setdefault(
                    key,
                    [],
                )

                for candidate in (merged[key], value):

                    if candidate not in values:

                        values.append(
                            deepcopy(candidate)
                        )

        return merged

    @classmethod
    def _merge(
        cls,
        existing: dict,
        incoming: dict,
    ) -> dict:

        merged = deepcopy(existing)

        # Merge metadata.

        merged["metadata"] = cls._merge_metadata(
            existing.get("metadata", {}),
            incoming.get("metadata", {}),
        )

        # Merge source references.

        source_references = [
            cls._source_reference(existing),
            cls._source_reference(incoming),
            *existing.get("metadata", {}).get("sources", []),
            *incoming.get("metadata", {}).get("sources", []),
        ]

        unique_sources = []

        seen_sources = set()

        for source in source_references:

            key = (
                source.get("provider"),
                source.get("external_id"),
                source.get("official_url"),
                source.get("source_url"),
                source.get("application_url"),
            )

            if key not in seen_sources:

                seen_sources.add(key)

                unique_sources.append(
                    deepcopy(source)
                )

        merged["metadata"]["sources"] = unique_sources

        # Merge required skills.

        merged["required_skills"] = cls._merge_list(
            existing.get("required_skills", []),
            incoming.get("required_skills", []),
        )

        # Merge optional information without overwriting
        # an existing non-empty value.

        for field in cls.MERGE_FIELDS:

            if (
                merged.get(field) is None
                and incoming.get(field) is not None
            ):

                merged[field] = deepcopy(
                    incoming[field]
                )

            elif (
                merged.get(field) is not None
                and incoming.get(field) is not None
                and merged[field] != incoming[field]
            ):

                conflicts = merged["metadata"].setdefault(
                    "field_conflicts",
                    {},
                )

                values = conflicts.setdefault(
                    field,
                    [],
                )

                for candidate in (
                    merged[field],
                    incoming[field],
                ):

                    if candidate not in values:

                        values.append(
                            deepcopy(candidate)
                        )

        # Merge eligibility without losing restrictions.

        merged["eligibility"] = cls._merge_eligibility(
            existing.get("eligibility", {}),
            incoming.get("eligibility", {}),
            merged["metadata"],
        )

        return merged

    @classmethod
    def deduplicate(
        cls,
        opportunities: list[Any],
    ) -> list[dict]:

        if not isinstance(opportunities, list):

            raise TypeError(
                "Expected a list of opportunities."
            )

        normalized = OpportunityNormalizer.normalize_many(
            opportunities
        )

        unique_opportunities = {}

        for opportunity in normalized:

            identity = OpportunityIdentityResolver.resolve(
                opportunity
            )

            if identity not in unique_opportunities:

                unique_opportunities[identity] = deepcopy(
                    opportunity
                )

            else:

                unique_opportunities[identity] = cls._merge(
                    unique_opportunities[identity],
                    opportunity,
                )

        return list(
            unique_opportunities.values()
        )