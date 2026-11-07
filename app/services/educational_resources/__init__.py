from app.services.educational_resources.discovery_exceptions import (
    ResourceDiscoveryError,
    ResourceDiscoveryProviderError,
    ResourceDiscoveryResponseError,
    ResourceDiscoveryUnavailableError,
    ResourceDiscoveryValidationError,
)

from app.services.educational_resources.discovery_service import (
    ResourceDiscoveryService,
)

from app.services.educational_resources.resource_mapper import (
    ExternalResourceMapper,
    ResourceMappingError,
)

from app.services.educational_resources.normalization import (
    ExternalResourceNormalizer,
    ResourceDeduplicationService,
    ResourceIdentityResolver,
    ResourceNormalizationError,
    ResourceTextNormalizer,
    ResourceURLNormalizationError,
    ResourceURLNormalizer,
)
from app.services.educational_resources.quality_assessor import (
    FreshnessPolicy,
    QualityWeights,
    ResourceQualityAssessment,
    ResourceQualityAssessor,
)
from app.services.educational_resources.relevance_ranker import (
    RelevanceAssessment,
    RelevanceWeights,
    ResourceRelevanceRanker,
)
from app.services.educational_resources.recommendation_service import (
    ResourceRecommendationService,
)

__all__ = [
    "ExternalResourceMapper",
    "ResourceMappingError",
    "ResourceDiscoveryService",
    "ResourceDiscoveryError",
    "ResourceDiscoveryProviderError",
    "ResourceDiscoveryResponseError",
    "ResourceDiscoveryUnavailableError",
    "ResourceDiscoveryValidationError",
    "ExternalResourceNormalizer",
    "ResourceDeduplicationService",
    "ResourceIdentityResolver",
    "ResourceNormalizationError",
    "ResourceTextNormalizer",
    "ResourceURLNormalizationError",
    "ResourceURLNormalizer",
    "FreshnessPolicy",
    "QualityWeights",
    "ResourceQualityAssessment",
    "ResourceQualityAssessor",
     "RelevanceAssessment",
    "RelevanceWeights",
    "ResourceRelevanceRanker",
    "ResourceRecommendationService",
]