"""
ScholarAI Recommendation Services.

Contains components for:
- Resource classification
- Rule configuration
- Learning context construction
- Rule evaluation
- Recommendation scoring
- Candidate filtering
- Recommendation ranking
- Recommendation explanations
"""

from app.services.recommendations.resource_classifier import (
    ResourceClassifier,
)

from app.services.recommendations.rule_config import (
    RecommendationRuleRegistry,
    build_example_rules,
)

from app.services.recommendations.context_builder import (
    LearningContextBuilder,
)

from app.services.recommendations.rule_evaluator import (
    RuleEvaluator,
    RuleEvaluationResult,
    RuleExecutionResult,
)

from app.services.recommendations.scoring_service import (
    RecommendationScoringService,
)

from app.services.recommendations.filtering_service import (
    RecommendationFilteringService,
)

from app.services.recommendations.ranking_service import (
    RankedRecommendation,
    RecommendationRankingService,
)

from app.services.recommendations.ranking_pipeline import (
    RecommendationRankingPipeline,
)

from app.services.recommendations.explanation_service import (
    RecommendationExplanationService,
)

from app.services.recommendations.explanation_pipeline import (
    RecommendationExplanationPipeline,
)
from app.services.recommendations.recommendation_service import (
    RecommendationApplicationService,
)

__all__ = [
    "ResourceClassifier",
    "RecommendationRuleRegistry",
    "build_example_rules",
    "LearningContextBuilder",
    "RuleEvaluator",
    "RuleEvaluationResult",
    "RuleExecutionResult",
    "RecommendationScoringService",
    "RecommendationFilteringService",
    "RecommendationRankingService",
    "RecommendationRankingPipeline",
    "RankedRecommendation",
    "RecommendationExplanationService",
    "RecommendationExplanationPipeline",
    "RecommendationApplicationService",
]