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

from app.services.recommendations.hybrid.aggregation import (
    HybridCandidateAggregator,
)

from app.services.recommendations.hybrid.scoring import (
    HybridScoringPipeline,
    HybridScoreNormalizer,
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


# ============================================================
# TEST DATA FACTORIES
# ============================================================

def make_candidate(
    title: str,
    component_scores: tuple[ComponentScore, ...],
) -> HybridCandidate:
    return HybridCandidate(
        resource_id=uuid4(),
        title=title,
        resource_type="article",
        component_scores=component_scores,
        provenance=(),
    )


def make_score(
    component: RecommendationComponent,
    value: float,
) -> ComponentScore:
    return ComponentScore(
        component=component,
        status=ComponentStatus.AVAILABLE,
        value=value,
        direction=ScoreDirection.HIGHER_IS_BETTER,
    )


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def scoring_pipeline() -> HybridScoringPipeline:
    normalizer = HybridScoreNormalizer(
        configurations={
            RULE: ScoreNormalizationConfig(0.0, 1.0),
            CONTENT: ScoreNormalizationConfig(0.0, 1.0),
            ML: ScoreNormalizationConfig(0.0, 1.0),
        }
    )

    weighting_engine = HybridWeightingEngine(
        HybridWeightConfig()
    )

    return HybridScoringPipeline(
        normalizer=normalizer,
        weighting_engine=weighting_engine,
    )


@pytest.fixture
def filtering_pipeline() -> HybridFilteringPipeline:
    return HybridFilteringPipeline(
        HybridEligibilityFilter()
    )


# ============================================================
# INTEGRATION TEST 1
# COMPLETE HYBRID RECOMMENDATION PIPELINE
# ============================================================

def test_complete_hybrid_pipeline_ranks_valid_candidates(
    scoring_pipeline: HybridScoringPipeline,
    filtering_pipeline: HybridFilteringPipeline,
) -> None:

    first = make_candidate(
        "Python Fundamentals",
        (
            make_score(RULE, 0.9),
            make_score(CONTENT, 0.8),
            make_score(ML, 0.85),
        ),
    )

    second = make_candidate(
        "Introduction to Programming",
        (
            make_score(RULE, 0.6),
            make_score(CONTENT, 0.7),
            make_score(ML, 0.65),
        ),
    )

    candidates = (first, second)

    # Step 1: Aggregate candidates.
    aggregator = HybridCandidateAggregator()

    aggregation_result = aggregator.aggregate(
        [candidates]
    )

    aggregated_candidates = aggregation_result.candidates

    assert len(aggregated_candidates) == 2

    # Step 2: Calculate hybrid scores.
    score_results = {
        candidate.resource_id: scoring_pipeline.score(candidate)
        for candidate in aggregated_candidates
    }

    assert len(score_results) == 2

    # Step 3: Resolve candidate eligibility.
    decisions = {
        candidate.resource_id: EligibilityDecision(
            resource_id=candidate.resource_id,
            is_valid=True,
            is_eligible=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        for candidate in aggregated_candidates
    }

    # Step 4: Apply eligibility filtering.
    filtering_results = filtering_pipeline.execute(
        tuple(
            candidate.resource_id
            for candidate in aggregated_candidates
        ),
        decisions,
    )

    assert len(filtering_results) == 2
    assert all(result.accepted for result in filtering_results)

    # Step 5: Rank candidates using hybrid scores.
    ranking_pipeline = HybridRankingPipeline()

    response = ranking_pipeline.execute(
        candidates=aggregated_candidates,
        score_results=score_results,
        filtering_results=filtering_results,
    )

    # Step 6: Validate ranking output.
    assert len(response.ranked_candidates) == 2

    first_ranked = response.ranked_candidates[0]
    second_ranked = response.ranked_candidates[1]

    # HybridScoreResult belongs to RankedHybridCandidate.score.
    assert (
        first_ranked.score.hybrid_score
        >= second_ranked.score.hybrid_score
    )

    assert first_ranked.rank == 1
    assert second_ranked.rank == 2

    assert response.total_received == 2
    assert response.total_accepted == 2
    assert response.total_excluded == 0


# ============================================================
# INTEGRATION TEST 2
# INVALID CANDIDATES MUST NOT BE RETURNED
# ============================================================

def test_invalid_candidate_is_not_returned(
    scoring_pipeline: HybridScoringPipeline,
    filtering_pipeline: HybridFilteringPipeline,
) -> None:

    valid_candidate = make_candidate(
        "Valid Resource",
        (
            make_score(RULE, 0.9),
        ),
    )

    invalid_candidate = make_candidate(
        "Invalid Resource",
        (
            make_score(RULE, 0.95),
        ),
    )

    candidates = (
        valid_candidate,
        invalid_candidate,
    )

    # Calculate scores for both candidates.
    score_results = {
        candidate.resource_id: scoring_pipeline.score(candidate)
        for candidate in candidates
    }

    # Define eligibility decisions.
    decisions = {
        valid_candidate.resource_id: EligibilityDecision(
            resource_id=valid_candidate.resource_id,
            is_valid=True,
            is_eligible=True,
            availability=AvailabilityStatus.AVAILABLE,
        ),

        invalid_candidate.resource_id: EligibilityDecision(
            resource_id=invalid_candidate.resource_id,
            is_valid=False,
            is_eligible=True,
            availability=AvailabilityStatus.AVAILABLE,
        ),
    }

    # Apply filtering.
    filtering_results = filtering_pipeline.execute(
        tuple(
            candidate.resource_id
            for candidate in candidates
        ),
        decisions,
    )

    # Rank only accepted candidates.
    response = HybridRankingPipeline().execute(
        candidates=candidates,
        score_results=score_results,
        filtering_results=filtering_results,
    )

    returned_ids = {
        item.resource.resource_id
        for item in response.ranked_candidates
    }

    assert valid_candidate.resource_id in returned_ids
    assert invalid_candidate.resource_id not in returned_ids

    assert response.total_received == 2
    assert response.total_accepted == 1
    assert response.total_excluded == 1


# ============================================================
# INTEGRATION TEST 3
# HARD ELIGIBILITY CONSTRAINTS OVERRIDE HIGH SCORES
# ============================================================

def test_hard_eligibility_constraints_override_high_score(
    scoring_pipeline: HybridScoringPipeline,
    filtering_pipeline: HybridFilteringPipeline,
) -> None:

    candidate = make_candidate(
        "High Score Ineligible Resource",
        (
            make_score(RULE, 1.0),
            make_score(CONTENT, 1.0),
            make_score(ML, 1.0),
        ),
    )

    # Calculate an excellent hybrid score.
    score_result = scoring_pipeline.score(candidate)

    assert score_result.hybrid_score == pytest.approx(1.0)

    # But the resource is explicitly ineligible.
    decision = EligibilityDecision(
        resource_id=candidate.resource_id,
        is_valid=True,
        is_eligible=False,
        availability=AvailabilityStatus.AVAILABLE,
    )

    # Apply hard eligibility filtering.
    filtering_results = filtering_pipeline.execute(
        (candidate.resource_id,),
        {
            candidate.resource_id: decision,
        },
    )

    # Attempt ranking.
    response = HybridRankingPipeline().execute(
        candidates=(candidate,),
        score_results={
            candidate.resource_id: score_result,
        },
        filtering_results=filtering_results,
    )

    # Ineligible resources must never appear in recommendations.
    assert response.ranked_candidates == ()

    assert response.total_received == 1
    assert response.total_accepted == 0
    assert response.total_excluded == 1