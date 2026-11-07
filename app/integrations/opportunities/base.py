import asyncio
import random

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.opportunity_provider_config import (
    OpportunityProviderSettings,
)

from app.integrations.opportunities.exceptions import (
    OpportunityProviderAuthenticationError,
    OpportunityProviderRateLimitError,
    OpportunityProviderResponseError,
    OpportunityProviderTimeoutError,
    OpportunityProviderUnavailableError,
)


class BaseOpportunityProvider(ABC):

    provider_name: str

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: OpportunityProviderSettings,
    ):

        self.client = client
        self.settings = settings

        self._semaphore = asyncio.Semaphore(
            settings.max_concurrency
        )

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        **filters,
    ) -> list[dict[str, Any]]:
        pass

    async def health_check(self) -> dict:

        return {
            "provider": self.provider_name,
            "status": "configured",
        }

    async def _request_json(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> dict[str, Any]:

        for attempt in range(self.settings.max_retries + 1):

            try:

                async with self._semaphore:

                    response = await self.client.request(
                        method,
                        url,
                        **kwargs,
                    )

                if response.status_code in (401, 403):

                    raise OpportunityProviderAuthenticationError(
                        f"{self.provider_name} authentication failed."
                    )

                if response.status_code == 429:

                    if attempt < self.settings.max_retries:

                        retry_after = response.headers.get("Retry-After")

                        try:
                            delay = float(retry_after)
                        except (TypeError, ValueError):
                            delay = self._retry_delay_value(attempt)

                        await asyncio.sleep(
                            min(max(delay, 0), self.settings.max_retry_delay)
                        )

                        continue

                    raise OpportunityProviderRateLimitError(
                        f"{self.provider_name} rate limit exceeded."
                    )

                if response.status_code >= 500:

                    if attempt < self.settings.max_retries:
                        await self._retry_delay(attempt)
                        continue

                    raise OpportunityProviderUnavailableError(
                        f"{self.provider_name} server unavailable."
                    )

                response.raise_for_status()

                try:
                    payload = response.json()
                except ValueError as exc:
                    raise OpportunityProviderResponseError(
                        f"{self.provider_name} returned invalid JSON."
                    ) from exc

                if not isinstance(payload, dict):
                    raise OpportunityProviderResponseError(
                        f"{self.provider_name} returned an invalid response structure."
                    )

                return payload

            except httpx.TimeoutException as exc:

                if attempt < self.settings.max_retries:
                    await self._retry_delay(attempt)
                    continue

                raise OpportunityProviderTimeoutError(
                    f"{self.provider_name} request timed out."
                ) from exc

            except httpx.TransportError as exc:

                if attempt < self.settings.max_retries:
                    await self._retry_delay(attempt)
                    continue

                raise OpportunityProviderUnavailableError(
                    f"{self.provider_name} transport failure."
                ) from exc

            except httpx.HTTPStatusError as exc:

                status_code = exc.response.status_code

                if status_code in (401, 403):
                    raise OpportunityProviderAuthenticationError(
                        f"{self.provider_name} authentication failed."
                    ) from exc

                if status_code == 429:
                    raise OpportunityProviderRateLimitError(
                        f"{self.provider_name} rate limit exceeded."
                    ) from exc

                if status_code >= 500:
                    raise OpportunityProviderUnavailableError(
                        f"{self.provider_name} server error."
                    ) from exc

                raise OpportunityProviderResponseError(
                    f"{self.provider_name} returned HTTP {status_code}."
                ) from exc

        raise OpportunityProviderUnavailableError(
            f"{self.provider_name} request failed."
        )

    def _retry_delay_value(self, attempt: int) -> float:

        delay = min(
            self.settings.base_retry_delay * (2 ** attempt),
            self.settings.max_retry_delay,
        )

        return delay + random.uniform(
            0,
            min(0.25, delay * 0.25),
        )

    async def _retry_delay(self, attempt: int):

        await asyncio.sleep(
            self._retry_delay_value(attempt)
        )