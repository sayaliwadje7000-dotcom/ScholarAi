from __future__ import annotations

from app.schemas.educational_resource_discovery import (
    ResourceDiscoveryRequest,
)
from app.schemas.educational_resources import (
    EducationalResourceListResponse,
)
from app.services.educational_resources.discovery_service import (
    ResourceDiscoveryService,
)


class ResourceRecommendationService:
    """
    Application service for recommending educational resources.

    Delegates external resource discovery and ranking to
    ResourceDiscoveryService.

    The discovery pipeline is responsible for:
    - Provider selection
    - External resource retrieval
    - Provider failure isolation
    - Resource filtering
    - Normalization and deduplication
    - Quality assessment
    - Relevance scoring and ranking

    This service provides a stable application-level interface
    for the API layer.
    """

    def __init__(
        self,
        discovery_service: ResourceDiscoveryService,
    ) -> None:
        if discovery_service is None:
            raise ValueError(
                "discovery_service cannot be None."
            )

        self.discovery_service = discovery_service

    async def recommend(
        self,
        request: ResourceDiscoveryRequest,
    ) -> EducationalResourceListResponse:
        """
        Discover and recommend educational resources.

        Args:
            request:
                Validated resource discovery request.

        Returns:
            Ranked educational resource response.
        """

        if not isinstance(
            request,
            ResourceDiscoveryRequest,
        ):
            raise TypeError(
                "request must be a ResourceDiscoveryRequest."
            )

        response = await self.discovery_service.discover(
            request
        )

        return response