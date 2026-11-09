from __future__ import annotations

from uuid import uuid4

from app.services.recommendations.hybrid.contracts import (
    ComponentScore,
    ComponentStatus,
    HybridCandidate,
    RecommendationComponent,
    ScoreDirection,
)

from app.services.recommendations.hybrid.orchestration import (
    HybridComponentProvider,
    HybridRecommendationOrchestrator,
    HybridRequestContext,
)

from app.services.recommendations.hybrid.aggregation import (
    HybridCandidateAggregator,
)

from app.services.recommendations.hybrid.filtering import (
    AvailabilityStatus,
    EligibilityDecision,
    HybridEligibilityFilter,
    HybridFilteringPipeline,
)

from app.services.recommendations.hybrid.ranking import (
    HybridRankingPipeline,
)

from app.services.recommendations.hybrid.scoring import (
    HybridScoringPipeline,
    HybridScoreNormalizer,
    HybridWeightConfig,
    HybridWeightingEngine,
    ScoreNormalizationConfig,
)


RULE = RecommendationComponent.RULE_BASED
CONTENT = RecommendationComponent.CONTENT_BASED
ML = RecommendationComponent.MACHINE_LEARNING


def make_candidate(component, score):
    return HybridCandidate(
        resource_id=uuid4(),
        title="Fallback Resource",
        resource_type="article",
        component_scores=(
            ComponentScore(
                component=component,
                status=ComponentStatus.AVAILABLE,
                value=score,
                direction=ScoreDirection.HIGHER_IS_BETTER,
            ),
        ),
        provenance=(),
    )


def build_orchestrator(providers):
    normalizer = HybridScoreNormalizer(
        configurations={
            RULE: ScoreNormalizationConfig(0.0, 1.0),
            CONTENT: ScoreNormalizationConfig(0.0, 1.0),
            ML: ScoreNormalizationConfig(0.0, 1.0),
        }
    )

    scoring = HybridScoringPipeline(
        normalizer=normalizer,
        weighting_engine=HybridWeightingEngine(
            HybridWeightConfig()
        ),
    )

    filtering = HybridFilteringPipeline(
        HybridEligibilityFilter()
    )

    def resolver(candidates, context):
        return {
            candidate.resource_id: EligibilityDecision(
                resource_id=candidate.resource_id,
                is_valid=True,
                is_eligible=True,
                availability=AvailabilityStatus.AVAILABLE,
            )
            for candidate in candidates
        }

    return HybridRecommendationOrchestrator(
        providers=providers,
        candidate_aggregator=HybridCandidateAggregator(),
        scoring_pipeline=scoring,
        filtering_pipeline=filtering,
        ranking_pipeline=HybridRankingPipeline(),
        eligibility_resolver=resolver,
    )


def test_single_available_provider_uses_fallback():
    candidate = make_candidate(RULE, 0.8)

    orchestrator = build_orchestrator(
        [
            HybridComponentProvider(
                component=RULE,
                discover=lambda context: [candidate],
            )
        ]
    )

    context = HybridRequestContext(
        user_id=uuid4(),
        query="Python",
        filters={},
        metadata={},
    )

    result = orchestrator.execute(context)

    assert len(result.ranked_candidates) == 1
    assert result.fallback_used is True


def test_no_available_candidate_does_not_create_fake_recommendations():
    def empty_provider(context):
        return []

    orchestrator = build_orchestrator(
        [
            HybridComponentProvider(
                component=RULE,
                discover=empty_provider,
            ),
            HybridComponentProvider(
                component=CONTENT,
                discover=empty_provider,
            ),
        ]
    )

    context = HybridRequestContext(
        user_id=uuid4(),
        query="Python",
        filters={},
        metadata={},
    )

    result = orchestrator.execute(context)

    assert result.ranked_candidates == ()
    assert result.total_candidates_discovered == 0
    assert result.total_candidates_returned == 0