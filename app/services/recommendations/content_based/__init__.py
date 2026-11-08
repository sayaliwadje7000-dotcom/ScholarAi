"""
Content-based recommendation infrastructure.

Phase 11 provides:
- Feature extraction.
- Feature normalization.
- Resource content representation.
- Semantic similarity infrastructure.
"""

from app.services.recommendations.content_based.feature_extractor import (
    ContentFeatureExtractor,
    ExtractedContentFeatures,
)

from app.services.recommendations.content_based.feature_normalizer import (
    ContentFeatureNormalizer,
)

from app.services.recommendations.content_based.representation_builder import (
    ContentSection,
    ResourceContentRepresentation,
    ResourceRepresentationBuilder,
)
from app.services.recommendations.content_based.similarity_models import (
    ResourceSimilarityResult,
    ResourceComparisonResult,
)

from app.services.recommendations.content_based.similarity_service import (
    ResourceSimilarityService,
    ResourceSimilarityError,
    ResourceSimilarityValidationError,
    ResourceEmbeddingNotFoundError,
)
from app.services.recommendations.content_based.scoring_models import (
    ContentBasedScoreResult,
    ContentSimilarityBreakdown,
)

from app.services.recommendations.content_based.scoring_service import (
    ContentBasedScoringError,
    ContentBasedScoringService,
    ContentScoringWeights,
)
from app.services.recommendations.content_based.candidate_models import (
    ContentBasedCandidate,
    ContentCandidateValidationError,
)

from app.services.recommendations.content_based.filtering_service import (
    ContentBasedFilteringService,
    ContentFilterCriteria,
    ContentFilteringError,
)

from app.services.recommendations.content_based.ranking_service import (
    ContentBasedRankingService,
    ContentRankingError,
    RankedContentRecommendation,
)
from app.services.recommendations.content_based.query_context import (
    ContentQueryContext,
    ContentQueryFilters,
    QueryContextValidationError,
)

from app.services.recommendations.content_based.query_context_service import (
    ContentQueryContextService,
    ContentQueryContextError,
    EmptyLearningIntentError,
    QueryEmbeddingError,
)
from app.services.recommendations.content_based.recommendation_service import (
    ContentBasedRecommendationService,
    ContentRecommendationServiceError,
)
from app.services.recommendations.ml.models import (
    BaselineModelConfig,
    RecommendationBaselineModel,
    RecommendationDummyBaseline,
    BaselineModelError,
    BaselineModelNotFittedError,
    InvalidTrainingDataError,
)
__all__ = [
    "ContentFeatureExtractor",
    "ExtractedContentFeatures",
    "ContentFeatureNormalizer",
    "ContentSection",
    "ResourceContentRepresentation",
    "ResourceRepresentationBuilder",
    "ResourceSimilarityResult",
"ResourceComparisonResult",
"ResourceSimilarityService",
"ResourceSimilarityError",
"ResourceSimilarityValidationError",
"ResourceEmbeddingNotFoundError",
 "ContentBasedRecommendationService",
    "ContentRecommendationServiceError",
    "BaselineModelConfig",
"RecommendationBaselineModel",
"RecommendationDummyBaseline",
"BaselineModelError",
"BaselineModelNotFittedError",
"InvalidTrainingDataError",
]