from __future__ import annotations

import asyncio

from datetime import datetime, timezone
from typing import Any

from app.schemas.educational_resource_discovery import (
    ResourceDiscoveryRequest,
)

from app.schemas.educational_resources import (
    EducationalResourceListResponse,
    EducationalResourceResponse,
)

from app.schemas.external_resources import (
    ExternalResource,
)

from app.services.educational_resources.discovery_exceptions import (
    ResourceDiscoveryResponseError,
    ResourceDiscoveryUnavailableError,
    ResourceDiscoveryValidationError,
)

from app.services.educational_resources.normalization import (
    ResourceDeduplicationService,
)

from app.services.educational_resources.quality_assessor import (
    ResourceQualityAssessor,
)

from app.services.educational_resources.relevance_ranker import (
    ResourceRelevanceRanker,
)


class ResourceDiscoveryService:
    """
    Orchestrates educational resource searches across
    multiple external provider adapters.

    Responsibilities:

    - Provider selection.
    - Concurrent searches.
    - Provider failure isolation.
    - Normalized result validation.
    - Search filtering.
    - Result aggregation.
    - Resource normalization and deduplication.
    - Quality, credibility and freshness assessment.
    - Relevance scoring and ranking.

    This service does not persist resources.
    """

    def __init__(
        self,
        registry,
        max_concurrent_providers: int = 4,
        deduplication_service: ResourceDeduplicationService | None = None,
        quality_assessor: ResourceQualityAssessor | None = None,
        relevance_ranker: ResourceRelevanceRanker | None = None,
    ) -> None:

        if registry is None:
            raise TypeError(
                "Provider registry is required."
            )

        if (
            isinstance(max_concurrent_providers, bool)
            or not isinstance(max_concurrent_providers, int)
            or max_concurrent_providers < 1
        ):
            raise ValueError(
                "Maximum concurrent providers must "
                "be a positive integer."
            )

        self.registry = registry

        self.max_concurrent_providers = (
            max_concurrent_providers
        )

        self.deduplication_service = (
            deduplication_service
            if deduplication_service is not None
            else ResourceDeduplicationService()
        )

        self.quality_assessor = (
            quality_assessor
            if quality_assessor is not None
            else ResourceQualityAssessor()
        )

        self.relevance_ranker = (
            relevance_ranker
            if relevance_ranker is not None
            else ResourceRelevanceRanker()
        )

    # ---------------------------------------------------------
    # Provider discovery
    # ---------------------------------------------------------

    def _available_provider_names(self) -> list[str]:
        """
        Obtain provider names from the existing registry.

        The registry's list() method is expected to return
        provider names or a mapping keyed by provider name.
        """

        available = self.registry.list()

        if isinstance(available, dict):
            names = list(available.keys())

        elif isinstance(available, (list, tuple, set)):
            names = []

            for item in available:

                if isinstance(item, str):
                    names.append(item)

                elif isinstance(item, tuple) and item:
                    names.append(item[0])

                else:
                    name = getattr(
                        item,
                        "name",
                        None,
                    )

                    if name is None:
                        name = getattr(
                            item,
                            "provider",
                            None,
                        )

                    if name is None:
                        raise ResourceDiscoveryValidationError(
                            "Registry returned a provider "
                            "without a recognizable name."
                        )

                    names.append(name)

        else:
            raise ResourceDiscoveryValidationError(
                "Provider registry returned an "
                "unsupported provider collection."
            )

        normalized = []

        for name in names:

            if not isinstance(name, str):
                raise ResourceDiscoveryValidationError(
                    "Provider names must be strings."
                )

            name = name.strip().casefold()

            if name and name not in normalized:
                normalized.append(name)

        return normalized

    def _select_providers(
        self,
        requested_providers: list[str] | None,
    ) -> list[str]:
        """
        Select configured providers.

        If providers are omitted, all registered providers
        are selected.
        """

        available = self._available_provider_names()

        if requested_providers is None:
            return available

        normalized_requested = {
            name.strip().casefold()
            for name in requested_providers
        }

        unavailable = (
            normalized_requested - set(available)
        )

        if unavailable:
            raise ResourceDiscoveryValidationError(
                "Unknown or unregistered providers: "
                + ", ".join(sorted(unavailable))
            )

        return [
            name
            for name in available
            if name in normalized_requested
        ]

    # ---------------------------------------------------------
    # Provider response validation
    # ---------------------------------------------------------

    @staticmethod
    def _validate_provider_results(
        provider_name: str,
        results: Any,
    ) -> list[ExternalResource]:
        """
        Validate provider output before aggregation.
        """

        if not isinstance(results, list):
            raise ResourceDiscoveryResponseError(
                f"Provider '{provider_name}' must return "
                "a list of ExternalResource objects."
            )

        validated = []

        for resource in results:

            if not isinstance(
                resource,
                ExternalResource,
            ):
                raise ResourceDiscoveryResponseError(
                    f"Provider '{provider_name}' returned "
                    "an invalid resource object."
                )

            if resource.provider.casefold() != provider_name:
                raise ResourceDiscoveryResponseError(
                    f"Provider '{provider_name}' returned "
                    "a resource with mismatched provenance."
                )

            validated.append(resource)

        return validated

    # ---------------------------------------------------------
    # Individual provider search
    # ---------------------------------------------------------

    async def _search_provider(
        self,
        provider_name: str,
        query: str,
        limit: int,
        semaphore: asyncio.Semaphore,
    ) -> tuple[str, list[ExternalResource], Exception | None]:
        """
        Search one provider.

        Failures are returned as data so one provider
        cannot cancel other provider searches.
        """

        async with semaphore:

            try:

                provider = self.registry.get(
                    provider_name
                )

                if provider is None:
                    raise ResourceDiscoveryValidationError(
                        f"Provider '{provider_name}' "
                        "could not be resolved."
                    )

                results = await provider.search(
                    query=query,
                    limit=limit,
                )

                validated = self._validate_provider_results(
                    provider_name,
                    results,
                )

                return (
                    provider_name,
                    validated,
                    None,
                )

            except Exception as exc:

                return (
                    provider_name,
                    [],
                    exc,
                )

    # ---------------------------------------------------------
    # Search filtering
    # ---------------------------------------------------------

    @staticmethod
    def _matches_filters(
        resource: ExternalResource,
        request: ResourceDiscoveryRequest,
    ) -> bool:
        """
        Apply explicit user-requested filters.

        This is deterministic filtering, not relevance
        scoring or recommendation ranking.
        """

        if (
            request.resource_types
            and resource.resource_type
            not in request.resource_types
        ):
            return False

        if request.language:

            if (
                resource.language is None
                or resource.language.casefold()
                != request.language.casefold()
            ):
                return False

        if request.subject:

            if (
                resource.subject is None
                or request.subject.casefold()
                not in resource.subject.casefold()
            ):
                return False

        return True

    # ---------------------------------------------------------
    # Main discovery operation
    # ---------------------------------------------------------

    async def discover(
        self,
        request: ResourceDiscoveryRequest,
    ) -> EducationalResourceListResponse:
        """
        Search selected providers concurrently.

        Processing pipeline:

        1. Provider selection.
        2. Concurrent provider searches.
        3. Provider response validation.
        4. Resource filtering.
        5. Resource normalization and deduplication.
        6. Quality, credibility and freshness assessment.
        7. Relevance scoring.
        8. Deterministic relevance ranking.
        9. API response conversion.
        """

        if not isinstance(
            request,
            ResourceDiscoveryRequest,
        ):
            raise TypeError(
                "Expected a ResourceDiscoveryRequest."
            )

        # -----------------------------------------------------
        # Step 1: Select providers.
        # -----------------------------------------------------

        provider_names = self._select_providers(
            request.providers
        )

        if not provider_names:
            raise ResourceDiscoveryUnavailableError(
                "No educational resource providers "
                "are currently available."
            )

        # -----------------------------------------------------
        # Step 2: Execute provider searches concurrently.
        # -----------------------------------------------------

        semaphore = asyncio.Semaphore(
            self.max_concurrent_providers
        )

        tasks = [
            self._search_provider(
                provider_name=name,
                query=request.query,
                limit=request.limit_per_provider,
                semaphore=semaphore,
            )
            for name in provider_names
        ]

        outcomes = await asyncio.gather(*tasks)

        successful_providers = []

        failed_providers = []

        aggregated_resources = []

        for (
            provider_name,
            resources,
            error,
        ) in outcomes:

            if error is not None:

                failed_providers.append(provider_name)

                continue

            successful_providers.append(provider_name)

            aggregated_resources.extend(
                resources
            )

        if not successful_providers:
            raise ResourceDiscoveryUnavailableError(
                "All selected educational resource "
                "providers failed."
            )

        # -----------------------------------------------------
        # Step 3: Apply requested resource filters.
        # -----------------------------------------------------

        filtered_resources = [
            resource
            for resource in aggregated_resources
            if self._matches_filters(
                resource,
                request,
            )
        ]

        # -----------------------------------------------------
        # Step 4: Normalize and deduplicate resources.
        # -----------------------------------------------------

        deduplicated_resources = (
            self.deduplication_service.deduplicate(
                filtered_resources
            )
        )

        # -----------------------------------------------------
        # Step 5: Assess resource quality.
        # -----------------------------------------------------

        quality_assessed_resources = (
            self.quality_assessor.assess_many(
                deduplicated_resources
            )
        )

        # -----------------------------------------------------
        # Step 6: Calculate relevance and rank resources.
        # -----------------------------------------------------

        ranked_resources = (
            self.relevance_ranker.rank(
                quality_assessed_resources,
                request.query,
            )
        )

        # -----------------------------------------------------
        # Step 7: Convert ranked resources into API responses.
        # -----------------------------------------------------

        response_resources = [
            EducationalResourceResponse.from_external_resource(
                resource
            )
            for resource in ranked_resources
        ]

        # -----------------------------------------------------
        # Step 8: Return the final discovery response.
        # -----------------------------------------------------

        return EducationalResourceListResponse(
            query=request.query,
            total_results=len(response_resources),
            resources=response_resources,
            providers_searched=successful_providers,
            providers_failed=failed_providers,
            retrieved_at=datetime.now(timezone.utc),
        )