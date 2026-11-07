from app.services.educational_resources.normalization.deduplication_service import (
    ResourceDeduplicationService,
)
from app.services.educational_resources.normalization.identity_resolver import (
    ResourceIdentityResolver,
)
from app.services.educational_resources.normalization.resource_normalizer import (
    ExternalResourceNormalizer,
    ResourceNormalizationError,
)
from app.services.educational_resources.normalization.text_normalizer import (
    ResourceTextNormalizer,
)
from app.services.educational_resources.normalization.url_normalizer import (
    ResourceURLNormalizationError,
    ResourceURLNormalizer,
)

__all__ = [
    "ExternalResourceNormalizer",
    "ResourceDeduplicationService",
    "ResourceIdentityResolver",
    "ResourceNormalizationError",
    "ResourceTextNormalizer",
    "ResourceURLNormalizationError",
    "ResourceURLNormalizer",
]