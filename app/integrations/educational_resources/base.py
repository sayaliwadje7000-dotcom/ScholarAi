import asyncio
import random

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.resource_provider_config import (
    ResourceProviderSettings,
)

from app.integrations.educational_resources.exceptions import (
    ResourceProviderAuthenticationError,
    ResourceProviderRateLimitError,
    ResourceProviderResponseError,
    ResourceProviderTimeoutError,
    ResourceProviderUnavailableError,
)

from app.schemas.external_resources import ExternalResource


class BaseResourceProvider(ABC):

    provider_name: str

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: ResourceProviderSettings,
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
    ) -> list[ExternalResource]:
        """
        Search external resources.
        """

    @abstractmethod
    def normalize(
        self,
        payload: dict[str, Any],
    ) -> ExternalResource | None:
        """
        Convert provider-specific payload
        into the common resource schema.
        """

    async def health_check(self) -> dict:

        return {
            "provider": self.provider_name,
            "status": "configured",
        }

    async def close(self) -> None:
        """
        HTTP client lifecycle is managed by the registry.
        """

    async def _request_json(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> dict:

        for attempt in range(
            self.settings.max_retries + 1
        ):

            try:

                async with self._semaphore:

                    response = await self.client.request(
                        method,
                        url,
                        **kwargs,
                    )

                if response.status_code in (401, 403):

                    raise ResourceProviderAuthenticationError(
                        f"{self.provider_name} authentication failed."
                    )

                if response.status_code == 429:

                    if attempt < self.settings.max_retries:

                        await self._retry_delay(attempt)

                        continue

                    raise ResourceProviderRateLimitError(
                        f"{self.provider_name} rate limit exceeded."
                    )

                if response.status_code >= 500:

                    if attempt < self.settings.max_retries:

                        await self._retry_delay(attempt)

                        continue

                    raise ResourceProviderUnavailableError(
                        f"{self.provider_name} server unavailable."
                    )

                response.raise_for_status()

                try:
                    payload = response.json()

                except ValueError as exc:

                    raise ResourceProviderResponseError(
                        f"{self.provider_name} returned invalid JSON."
                    ) from exc

                if not isinstance(payload, dict):

                    raise ResourceProviderResponseError(
                        f"{self.provider_name} returned "
                        "an invalid response structure."
                    )

                return payload

            except httpx.TimeoutException as exc:

                if attempt < self.settings.max_retries:

                    await self._retry_delay(attempt)

                    continue

                raise ResourceProviderTimeoutError(
                    f"{self.provider_name} request timed out."
                ) from exc

            except httpx.TransportError as exc:

                if attempt < self.settings.max_retries:

                    await self._retry_delay(attempt)

                    continue

                raise ResourceProviderUnavailableError(
                    f"{self.provider_name} transport failure."
                ) from exc

            except httpx.HTTPStatusError as exc:

                status_code = exc.response.status_code

                if status_code in (401, 403):

                    raise ResourceProviderAuthenticationError(
                        f"{self.provider_name} authentication failed."
                    ) from exc

                if status_code == 429:

                    raise ResourceProviderRateLimitError(
                        f"{self.provider_name} rate limit exceeded."
                    ) from exc

                if status_code >= 500:

                    raise ResourceProviderUnavailableError(
                        f"{self.provider_name} server error."
                    ) from exc

                raise ResourceProviderResponseError(
                    f"{self.provider_name} returned "
                    f"HTTP {status_code}."
                ) from exc

        raise ResourceProviderUnavailableError(
            f"{self.provider_name} request failed."
        )

    async def _retry_delay(
        self,
        attempt: int,
    ):

        delay = min(
            self.settings.base_retry_delay
            * (2 ** attempt),
            self.settings.max_retry_delay,
        )

        delay += random.uniform(
            0,
            min(0.25, delay * 0.25),
        )

        await asyncio.sleep(delay)