from __future__ import annotations

import asyncio

from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.schemas.opportunities.discovery import (
    OpportunityDiscoveryRequest,
    OpportunityDiscoveryResponse,
    OpportunityProviderFailure,
)

from app.schemas.opportunities.opportunity import (
    OpportunityCreate,
)

from app.services.opportunities.discovery_exceptions import (
    OpportunityDiscoveryConfigurationError,
    OpportunityDiscoveryResponseError,
    OpportunityDiscoveryUnavailableError,
    OpportunityDiscoveryValidationError,
)


class OpportunityDiscoveryService:
    """
    Coordinates live opportunity searches across registered
    external opportunity providers.

    Responsibilities:

    - Provider discovery and selection.
    - Concurrent provider execution.
    - Concurrency limiting.
    - Provider failure isolation.
    - Provider response validation.
    - Opportunity type filtering.
    - Location filtering.
    - Remote opportunity filtering.
    - Result aggregation.
    - Result limiting.

    This service does not:

    - Persist opportunities.
    - Deduplicate opportunities.
    - Normalize duplicate identities.
    - Evaluate eligibility.
    - Determine deadline freshness.
    - Perform relevance scoring.
    - Perform recommendation ranking.
    """

    def __init__(
        self,
        registry,
        max_concurrent_providers: int = 4,
    ) -> None:

        if registry is None:
            raise TypeError(
                "Opportunity provider registry is required."
            )

        if (
            isinstance(max_concurrent_providers, bool)
            or not isinstance(max_concurrent_providers, int)
            or max_concurrent_providers < 1
        ):
            raise ValueError(
                "max_concurrent_providers must be "
                "a positive integer."
            )

        self.registry = registry

        self.max_concurrent_providers = (
            max_concurrent_providers
        )

    # ---------------------------------------------------------
    # PROVIDER DISCOVERY
    # ---------------------------------------------------------

    def _available_provider_names(self) -> list[str]:
        """
        Obtain provider names from the configured registry.

        Supports the provider-listing conventions used by
        registry implementations without requiring the
        discovery service to own provider registration.
        """

        if hasattr(self.registry, "list_providers"):

            available = self.registry.list_providers()

        elif hasattr(self.registry, "list"):

            available = self.registry.list()

        else:

            raise OpportunityDiscoveryConfigurationError(
                "Opportunity registry does not expose "
                "a provider listing method."
            )

        if isinstance(available, dict):

            names = list(available.keys())

        elif isinstance(
            available,
            (list, tuple, set),
        ):

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

                        raise OpportunityDiscoveryConfigurationError(
                            "Registry returned a provider "
                            "without a recognizable name."
                        )

                    names.append(name)

        else:

            raise OpportunityDiscoveryConfigurationError(
                "Registry returned an unsupported provider collection."
            )

        normalized = []

        seen = set()

        for name in names:

            if not isinstance(name, str):

                raise OpportunityDiscoveryConfigurationError(
                    "Provider names must be strings."
                )

            name = name.strip().casefold()

            if not name:
                continue

            if name not in seen:

                seen.add(name)

                normalized.append(name)

        return sorted(normalized)

    # ---------------------------------------------------------
    # PROVIDER SELECTION
    # ---------------------------------------------------------

    def _select_providers(
        self,
        requested_providers: list[str] | None,
    ) -> list[str]:
        """
        Select registered providers.

        If providers are omitted, every registered provider
        is selected.

        Explicitly requested but unavailable providers
        cause a validation error.
        """

        available = self._available_provider_names()

        if not available:

            raise OpportunityDiscoveryUnavailableError(
                "No opportunity providers are currently configured."
            )

        if requested_providers is None:

            return available

        requested = {
            provider.strip().casefold()
            for provider in requested_providers
        }

        unavailable = requested - set(available)

        if unavailable:

            raise OpportunityDiscoveryValidationError(
                "Unknown or unavailable opportunity providers: "
                + ", ".join(sorted(unavailable))
            )

        return [
            provider
            for provider in available
            if provider in requested
        ]

    # ---------------------------------------------------------
    # PROVIDER RESPONSE VALIDATION
    # ---------------------------------------------------------

    @staticmethod
    def _validate_provider_results(
        provider_name: str,
        results: Any,
    ) -> list[OpportunityCreate]:
        """
        Validate provider output before aggregation.

        Providers must return a list of opportunity records
        compatible with OpportunityCreate.

        The service validates records but does not persist them.
        """

        if not isinstance(results, list):

            raise OpportunityDiscoveryResponseError(
                f"Provider '{provider_name}' must return "
                "a list of opportunities."
            )

        validated = []

        for index, opportunity in enumerate(results):

            try:

                if isinstance(
                    opportunity,
                    OpportunityCreate,
                ):

                    validated_opportunity = opportunity

                else:

                    validated_opportunity = (
                        OpportunityCreate.model_validate(
                            opportunity
                        )
                    )

            except (ValidationError, TypeError, ValueError) as exc:

                raise OpportunityDiscoveryResponseError(
                    f"Provider '{provider_name}' returned "
                    f"an invalid opportunity at index {index}."
                ) from exc

            if (
                validated_opportunity.provider
                .strip()
                .casefold()
                != provider_name
            ):

                raise OpportunityDiscoveryResponseError(
                    f"Provider '{provider_name}' returned "
                    "an opportunity with mismatched provenance."
                )

            validated.append(validated_opportunity)

        return validated

    # ---------------------------------------------------------
    # FILTERING
    # ---------------------------------------------------------

    @staticmethod
    def _matches_filters(
        opportunity: OpportunityCreate,
        request: OpportunityDiscoveryRequest,
    ) -> bool:
        """
        Apply explicit discovery filters.

        These are deterministic filters, not relevance scoring.
        """

        if (
            request.opportunity_types
            and opportunity.opportunity_type
            not in request.opportunity_types
        ):

            return False

        if request.location:

            if not opportunity.location:

                return False

            if (
                request.location.casefold()
                not in opportunity.location.casefold()
            ):

                return False

        if request.is_remote is not None:

            if opportunity.is_remote != request.is_remote:

                return False

        return True

    # ---------------------------------------------------------
    # INDIVIDUAL PROVIDER SEARCH
    # ---------------------------------------------------------

    async def _search_provider(
        self,
        provider_name: str,
        request: OpportunityDiscoveryRequest,
        semaphore: asyncio.Semaphore,
    ) -> tuple[
        str,
        list[OpportunityCreate],
        Exception | None,
    ]:
        """
        Search one provider.

        Provider failures are returned as data rather than
        propagated, preventing one provider from cancelling
        other searches.
        """

        async with semaphore:

            try:

                provider = self.registry.get(
                    provider_name
                )

                if provider is None:

                    raise OpportunityDiscoveryConfigurationError(
                        f"Provider '{provider_name}' "
                        "could not be resolved."
                    )

                results = await provider.search(
                    query=request.query,
                    limit=request.limit_per_provider,
                )

                validated = self._validate_provider_results(
                    provider_name=provider_name,
                    results=results,
                )

                return (
                    provider_name,
                    validated,
                    None,
                )

            except asyncio.CancelledError:

                # Cancellation must propagate. Do not swallow
                # task cancellation during application shutdown.
                raise

            except Exception as exc:

                return (
                    provider_name,
                    [],
                    exc,
                )

    # ---------------------------------------------------------
    # MAIN DISCOVERY OPERATION
    # ---------------------------------------------------------

    async def discover(
        self,
        request: OpportunityDiscoveryRequest,
    ) -> OpportunityDiscoveryResponse:
        """
        Discover opportunities across selected providers.

        Pipeline:

        1. Validate request.
        2. Select configured providers.
        3. Execute provider searches concurrently.
        4. Isolate individual provider failures.
        5. Validate provider results.
        6. Apply explicit filters.
        7. Aggregate results.
        8. Enforce the overall result limit.
        9. Return discovery response.
        """

        if not isinstance(
            request,
            OpportunityDiscoveryRequest,
        ):

            raise TypeError(
                "Expected an OpportunityDiscoveryRequest."
            )

        provider_names = self._select_providers(
            request.providers
        )

        if not provider_names:

            raise OpportunityDiscoveryUnavailableError(
                "No opportunity providers were selected."
            )

        semaphore = asyncio.Semaphore(
            self.max_concurrent_providers
        )

        tasks = [
            self._search_provider(
                provider_name=provider_name,
                request=request,
                semaphore=semaphore,
            )
            for provider_name in provider_names
        ]

        outcomes = await asyncio.gather(*tasks)

        successful_providers = []

        failed_providers = []

        provider_failures = []

        aggregated_opportunities = []

        for (
            provider_name,
            opportunities,
            error,
        ) in outcomes:

            if error is not None:

                failed_providers.append(provider_name)

                provider_failures.append(
                    OpportunityProviderFailure(
                        provider=provider_name,
                        error_type=type(error).__name__,
                        message=(
                            "Opportunity provider search failed."
                        ),
                    )
                )

                continue

            successful_providers.append(provider_name)

            aggregated_opportunities.extend(
                opportunities
            )

        # A provider that returns an empty list is still
        # considered successful. Empty results are not errors.

        if not successful_providers:

            raise OpportunityDiscoveryUnavailableError(
                "All selected opportunity providers failed."
            )

        # -----------------------------------------------------
        # APPLY REQUESTED FILTERS
        # -----------------------------------------------------

        filtered_opportunities = [
            opportunity
            for opportunity in aggregated_opportunities
            if self._matches_filters(
                opportunity,
                request,
            )
        ]

        # -----------------------------------------------------
        # ENFORCE OVERALL RESULT LIMIT
        # -----------------------------------------------------

        limited_opportunities = (
            filtered_opportunities[:request.max_results]
        )

        # -----------------------------------------------------
        # BUILD DISCOVERY RESPONSE
        # -----------------------------------------------------

        return OpportunityDiscoveryResponse(
            query=request.query,
            total_results=len(limited_opportunities),
            opportunities=limited_opportunities,
            providers_requested=provider_names,
            providers_searched=successful_providers,
            providers_failed=failed_providers,
            provider_failures=provider_failures,
            retrieved_at=datetime.now(timezone.utc),
        )