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
    ProviderConfigurationError,
    HybridOrchestrationError,
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


# ============================================================
# TEST FACTORIES
# ============================================================

def make_candidate(
    component: RecommendationComponent,
    value: float,
    title: str = "Resource",
) -> HybridCandidate:

    return HybridCandidate(
        resource_id=uuid4(),
        title=title,
        resource_type="article",
        component_scores=(
            ComponentScore(
                component=component,
                status=ComponentStatus.AVAILABLE,
                value=value,
                direction=ScoreDirection.HIGHER_IS_BETTER,
            ),
        ),
        provenance=(),
    )


def make_context() -> HybridRequestContext:

    return HybridRequestContext(
        user_id=uuid4(),
        query="Python data structures",
        filters={},
        metadata={},
    )


def make_provider(
    component: RecommendationComponent,
    discover,
    enabled: bool = True,
) -> HybridComponentProvider:

    return HybridComponentProvider(
        component=component,
        discover=discover,
        enabled=enabled,
    )


def make_orchestrator(providers):

    normalizer = HybridScoreNormalizer(
        configurations={
            RecommendationComponent.RULE_BASED:
                ScoreNormalizationConfig(0.0, 1.0),

            RecommendationComponent.CONTENT_BASED:
                ScoreNormalizationConfig(0.0, 1.0),

            RecommendationComponent.MACHINE_LEARNING:
                ScoreNormalizationConfig(0.0, 1.0),
        }
    )

    weighting_engine = HybridWeightingEngine(
        HybridWeightConfig()
    )

    scoring_pipeline = HybridScoringPipeline(
        normalizer=normalizer,
        weighting_engine=weighting_engine,
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


# ============================================================
# ORCHESTRATION TESTS
# ============================================================

class TestHybridRecommendationOrchestrator:

    def test_single_provider_can_produce_recommendations(self):

        candidate = make_candidate(
            RecommendationComponent.RULE_BASED,
            0.8,
        )

        providers = [
            make_provider(
                RecommendationComponent.RULE_BASED,
                lambda context: [candidate],
            )
        ]

        orchestrator = make_orchestrator(providers)

        result = orchestrator.execute(make_context())

        assert len(result.ranked_candidates) == 1
        assert result.total_candidates_discovered == 1
        assert result.total_candidates_returned == 1
        assert result.fallback_used is True

    def test_failed_provider_does_not_stop_other_providers(self):

        candidate = make_candidate(
            RecommendationComponent.CONTENT_BASED,
            0.9,
        )

        def failing_provider(context):
            raise RuntimeError("Simulated provider failure")

        providers = [
            make_provider(
                RecommendationComponent.RULE_BASED,
                failing_provider,
            ),
            make_provider(
                RecommendationComponent.CONTENT_BASED,
                lambda context: [candidate],
            ),
        ]

        orchestrator = make_orchestrator(providers)

        result = orchestrator.execute(make_context())

        assert len(result.ranked_candidates) == 1
        assert result.fallback_used is True

        failed_reports = [
            report
            for report in result.component_reports
            if report.status == ComponentExecutionStatus.FAILED
        ]

        assert len(failed_reports) == 1
        assert failed_reports[0].error_type == "RuntimeError"

    def test_empty_provider_does_not_stop_other_providers(self):

        candidate = make_candidate(
            RecommendationComponent.RULE_BASED,
            0.7,
        )

        providers = [
            make_provider(
                RecommendationComponent.RULE_BASED,
                lambda context: [candidate],
            ),
            make_provider(
                RecommendationComponent.CONTENT_BASED,
                lambda context: [],
            ),
        ]

        orchestrator = make_orchestrator(providers)

        result = orchestrator.execute(make_context())

        assert result.total_candidates_returned == 1

        empty_reports = [
            report
            for report in result.component_reports
            if report.status == ComponentExecutionStatus.EMPTY
        ]

        assert len(empty_reports) == 1

    def test_no_candidates_returns_valid_empty_result(self):

        providers = [
            make_provider(
                RecommendationComponent.RULE_BASED,
                lambda context: [],
            )
        ]

        orchestrator = make_orchestrator(providers)

        result = orchestrator.execute(make_context())

        assert result.ranked_candidates == ()
        assert result.total_candidates_discovered == 0
        assert result.total_candidates_returned == 0

    def test_provider_malformed_output_is_isolated(self):

        candidate = make_candidate(
            RecommendationComponent.CONTENT_BASED,
            0.9,
        )

        providers = [
            make_provider(
                RecommendationComponent.RULE_BASED,
                lambda context: {"invalid": "output"},
            ),
            make_provider(
                RecommendationComponent.CONTENT_BASED,
                lambda context: [candidate],
            ),
        ]

        orchestrator = make_orchestrator(providers)

        result = orchestrator.execute(make_context())

        assert result.total_candidates_returned == 1

        failed_reports = [
            report
            for report in result.component_reports
            if report.status == ComponentExecutionStatus.FAILED
        ]

        assert len(failed_reports) == 1

    def test_invalid_context_is_rejected(self):

        provider = make_provider(
            RecommendationComponent.RULE_BASED,
            lambda context: [],
        )

        orchestrator = make_orchestrator([provider])

        with pytest.raises(
            (HybridOrchestrationError, TypeError, ValueError)
        ):
            orchestrator.execute(None)

    def test_duplicate_provider_configuration_is_rejected(self):

        provider = make_provider(
            RecommendationComponent.RULE_BASED,
            lambda context: [],
        )

        with pytest.raises(ProviderConfigurationError):

            make_orchestrator(
                [
                    provider,
                    provider,
                ]
            )

    def test_disabled_provider_is_reported(self):

        candidate = make_candidate(
            RecommendationComponent.CONTENT_BASED,
            0.8,
        )

        providers = [
            make_provider(
                RecommendationComponent.RULE_BASED,
                lambda context: [],
                enabled=False,
            ),
            make_provider(
                RecommendationComponent.CONTENT_BASED,
                lambda context: [candidate],
            ),
        ]

        orchestrator = make_orchestrator(providers)

        result = orchestrator.execute(make_context())

        disabled_reports = [
            report
            for report in result.component_reports
            if report.component == RecommendationComponent.RULE_BASED
            and report.status == ComponentExecutionStatus.DISABLED
        ]

        assert len(disabled_reports) == 1
        assert result.total_candidates_returned == 1