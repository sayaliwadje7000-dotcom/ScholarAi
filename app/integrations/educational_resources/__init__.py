from app.integrations.educational_resources.base import (
    BaseResourceProvider,
)

from app.integrations.educational_resources.registry import (
    ResourceProviderRegistry,
)

from app.schemas.external_resources import (
    ExternalResource,
    ExternalResourceType,
    ExternalAccessType,
)


__all__ = [
    "BaseResourceProvider",
    "ResourceProviderRegistry",
    "ExternalResource",
    "ExternalResourceType",
    "ExternalAccessType",
]