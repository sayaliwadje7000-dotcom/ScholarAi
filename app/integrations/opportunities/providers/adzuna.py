from typing import Any

import httpx

from app.core.opportunity_provider_config import (
    OpportunityProviderSettings,
)

from app.integrations.opportunities.base import (
    BaseOpportunityProvider,
)

from app.integrations.opportunities.exceptions import (
    OpportunityProviderConfigurationError,
    OpportunityProviderResponseError,
)


class AdzunaProvider(BaseOpportunityProvider):

    provider_name = "adzuna"

    BASE_URL = "https://api.adzuna.com/v1/api"

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: OpportunityProviderSettings,
    ):

        super().__init__(
            client=client,
            settings=settings,
        )

        if not settings.adzuna_configured:

            raise OpportunityProviderConfigurationError(
                "Adzuna credentials are not configured."
            )

        self.app_id = settings.adzuna_app_id
        self.app_key = settings.adzuna_app_key

        self.country = settings.adzuna_country

    async def search(
        self,
        query: str,
        limit: int = 10,
        **filters,
    ) -> list[dict[str, Any]]:

        query = query.strip() if query else ""

        if not query:
            return []

        limit = max(
            1,
            min(
                limit,
                self.settings.max_results_per_provider,
            ),
        )

        page = filters.get("page", 1)

        if not isinstance(page, int) or isinstance(page, bool) or page < 1:

            raise OpportunityProviderResponseError(
                "Adzuna page must be a positive integer."
            )

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": query,
            "results_per_page": limit,
            "content-type": "application/json",
        }

        location = filters.get("location")

        if location:
            location = str(location).strip()

            if location:
                params["where"] = location

        url = (
            f"{self.BASE_URL}/jobs/"
            f"{self.country}/search/{page}"
        )

        payload = await self._request_json(
            "GET",
            url,
            params=params,
        )

        results = payload.get("results")

        if not isinstance(results, list):

            raise OpportunityProviderResponseError(
                "Adzuna response does not contain a valid results array."
            )

        return [
            record
            for record in results
            if isinstance(record, dict)
        ][:limit]

    async def health_check(self) -> dict:

        return {
            "provider": self.provider_name,
            "status": "configured",
            "country": self.country,
        }