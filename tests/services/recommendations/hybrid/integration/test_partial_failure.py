from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.recommendations.hybrid.contracts import (
    ComponentScore,
    ComponentStatus,
    HybridCandidate,
    RecommendationComponent,
    ScoreDirection,
)

from app.services.recommendations.hybrid.orchestration import (
    ComponentExecutionStatus,
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
        title="Python Learning Resource",
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


def make_orchestrator(providers):
    normalizer = HybridScoreNormalizer(
        configurations={
            RULE: ScoreNormalizationConfig(0.0, 1.0),
            CONTENT: ScoreNormalizationConfig(0.0, 1.0),
            ML: ScoreNormalizationConfig(0.0, 1.0),
        }
    )

    scoring_pipeline = HybridScoringPipeline(
        normalizer=normalizer,
        weighting_engine=HybridWeightingEngine(
            HybridWeightConfig()
        ),
    )

    filtering_pipeline = HybridFilteringPipeline(
        HybridEligibilityFilter()
    )

    def eligibility_resolver(candidates, context):
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
        scoring_pipeline=scoring_pipeline,
        filtering_pipeline=filtering_pipeline,
        ranking_pipeline=HybridRankingPipeline(),
        eligibility_resolver=eligibility_resolver,
    )


def make_context():
    return HybridRequestContext(
        user_id=uuid4(),
        query="Python data structures",
        filters={},
        metadata={},
    )


def test_content_provider_failure_does_not_stop_rule_provider():
    candidate = make_candidate(RULE, 0.9)

    def failing_content_provider(context):
        raise RuntimeError("Content provider unavailable")

    providers = [
        HybridComponentProvider(
            component=RULE,
            discover=lambda context: [candidate],
        ),
        HybridComponentProvider(
            component=CONTENT,
            discover=failing_content_provider,
        ),
    ]

    result = make_orchestrator(providers).execute(
        make_context()
    )

    assert len(result.ranked_candidates) == 1

    failed_reports = [
        report
        for report in result.component_reports
        if report.component == CONTENT
        and report.status == ComponentExecutionStatus.FAILED
    ]

    assert len(failed_reports) == 1
    assert failed_reports[0].error_type == "RuntimeError"


def test_ml_failure_does_not_remove_available_candidates():
    candidate = make_candidate(CONTENT, 0.85)

    def failing_ml_provider(context):
        raise RuntimeError("ML inference unavailable")

    providers = [
        HybridComponentProvider(
            component=CONTENT,
            discover=lambda context: [candidate],
        ),
        HybridComponentProvider(
            component=ML,
            discover=failing_ml_provider,
        ),
    ]

    result = make_orchestrator(providers).execute(
        make_context()
    )

    assert len(result.ranked_candidates) == 1
    assert result.fallback_used is True

    assert any(
        report.component == ML
        and report.status == ComponentExecutionStatus.FAILED
        for report in result.component_reports
    )


def test_all_failed_providers_return_valid_empty_result():
    def failing_provider(context):
        raise RuntimeError("Provider unavailable")

    providers = [
        HybridComponentProvider(
            component=RULE,
            discover=failing_provider,
        ),
        HybridComponentProvider(
            component=CONTENT,
            discover=failing_provider,
        ),
        HybridComponentProvider(
            component=ML,
            discover=failing_provider,
        ),
    ]

    result = make_orchestrator(providers).execute(
        make_context()
    )

    assert result.ranked_candidates == ()
    assert result.total_candidates_returned == 0

    assert all(
        report.status == ComponentExecutionStatus.FAILED
        for report in result.component_reports
    )