from __future__ import annotations

from uuid import uuid4

from app.services.recommendations.hybrid.contracts import (
    ComponentScore,
    ComponentStatus,
    HybridCandidate,
    RecommendationComponent,
    ScoreDirection,
)

from app.services.recommendations.hybrid.scoring import (
    HybridScoreNormalizer,
    HybridScoringPipeline,
    HybridWeightConfig,
    HybridWeightingEngine,
    ScoreNormalizationConfig,
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


RULE = RecommendationComponent.RULE_BASED
CONTENT = RecommendationComponent.CONTENT_BASED
ML = RecommendationComponent.MACHINE_LEARNING


def make_candidate(title, score):
    return HybridCandidate(
        resource_id=uuid4(),
        title=title,
        resource_type="article",
        component_scores=(
            ComponentScore(
                component=RULE,
                status=ComponentStatus.AVAILABLE,
                value=score,
                direction=ScoreDirection.HIGHER_IS_BETTER,
            ),
        ),
        provenance=(),
    )


def test_ranking_is_deterministic():
    candidates = (
        make_candidate("Python A", 0.8),
        make_candidate("Python B", 0.8),
        make_candidate("Python C", 0.5),
    )

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

    scores = {
        candidate.resource_id: scoring.score(candidate)
        for candidate in candidates
    }

    decisions = {
        candidate.resource_id: EligibilityDecision(
            resource_id=candidate.resource_id,
            is_valid=True,
            is_eligible=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        for candidate in candidates
    }

    filtering = HybridFilteringPipeline(
        HybridEligibilityFilter()
    )

    filtering_results = filtering.execute(
        tuple(candidate.resource_id for candidate in candidates),
        decisions,
    )

    pipeline = HybridRankingPipeline()

    first_result = pipeline.execute(
        candidates=candidates,
        score_results=scores,
        filtering_results=filtering_results,
    )

    second_result = pipeline.execute(
        candidates=candidates,
        score_results=scores,
        filtering_results=filtering_results,
    )

    first_order = [
        item.resource.resource_id
        for item in first_result.ranked_candidates
    ]

    second_order = [
        item.resource.resource_id
        for item in second_result.ranked_candidates
    ]

    assert first_order == second_order