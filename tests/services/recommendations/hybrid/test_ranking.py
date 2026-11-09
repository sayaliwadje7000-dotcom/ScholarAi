from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.hybrid.contracts import (
    HybridCandidate,
    RecommendationComponent,
)

from app.services.recommendations.hybrid.filtering import (
    AvailabilityStatus,
    EligibilityDecision,
    FilteringResult,
)

from app.services.recommendations.hybrid.ranking import (
    HybridRankingError,
    HybridRankingPipeline,
)

from app.services.recommendations.hybrid.scoring import (
    ComponentContribution,
    HybridScoreResult,
)


def make_candidate(
    title="Test resource",
    resource_id=None,
):
    return HybridCandidate(
        resource_id=resource_id or uuid4(),
        title=title,
        resource_type="article",
        component_scores=(),
        provenance=(),
        canonical_url=None,
        description=None,
        metadata={},
        discovered_at=datetime.now(timezone.utc),
    )


def make_score(
    resource_id,
    hybrid_score,
    relevance=0.5,
    quality=0.5,
):
    contributions = (
        ComponentContribution(
            component=RecommendationComponent.CONTENT_BASED,
            normalized_score=relevance,
            configured_weight=0.30,
            effective_weight=0.50,
            weighted_contribution=relevance * 0.50,
        ),
        ComponentContribution(
            component=RecommendationComponent.RULE_BASED,
            normalized_score=quality,
            configured_weight=0.30,
            effective_weight=0.50,
            weighted_contribution=quality * 0.50,
        ),
    )

    return HybridScoreResult(
        resource_id=resource_id,
        hybrid_score=hybrid_score,
        normalized_scores=(),
        contributions=contributions,
        available_components=(
            RecommendationComponent.CONTENT_BASED,
            RecommendationComponent.RULE_BASED,
        ),
        excluded_components=(),
        configured_weight_total=0.60,
        effective_weight_total=1.0,
    )


def make_filter(resource_id, accepted=True):
    return FilteringResult(
        resource_id=resource_id,
        accepted=accepted,
        exclusion_reasons=(
            () if accepted else ("resource_invalid",)
        ),
        warnings=(),
    )


class TestHybridRankingPipeline:

    def setup_method(self):
        self.pipeline = HybridRankingPipeline()

    def test_ranks_candidates_by_hybrid_score(self):
        first = make_candidate("First")
        second = make_candidate("Second")

        result = self.pipeline.execute(
            candidates=(first, second),
            score_results={
                first.resource_id: make_score(
                    first.resource_id,
                    0.60,
                ),
                second.resource_id: make_score(
                    second.resource_id,
                    0.90,
                ),
            },
            filtering_results=(
                make_filter(first.resource_id),
                make_filter(second.resource_id),
            ),
        )

        assert result.ranked_candidates[0].resource.title == "Second"
        assert result.ranked_candidates[0].rank == 1
        assert result.ranked_candidates[1].rank == 2

    def test_excludes_rejected_candidate(self):
        first = make_candidate("Valid")
        second = make_candidate("Invalid")

        result = self.pipeline.execute(
            candidates=(first, second),
            score_results={
                first.resource_id: make_score(
                    first.resource_id,
                    0.50,
                ),
                second.resource_id: make_score(
                    second.resource_id,
                    1.00,
                ),
            },
            filtering_results=(
                make_filter(first.resource_id),
                make_filter(
                    second.resource_id,
                    accepted=False,
                ),
            ),
        )

        assert len(result.ranked_candidates) == 1
        assert result.ranked_candidates[0].resource.title == "Valid"
        assert result.total_excluded == 1

    def test_high_score_cannot_override_hard_filter(self):
        candidate = make_candidate()

        result = self.pipeline.execute(
            candidates=(candidate,),
            score_results={
                candidate.resource_id: make_score(
                    candidate.resource_id,
                    1.00,
                )
            },
            filtering_results=(
                make_filter(
                    candidate.resource_id,
                    accepted=False,
                ),
            ),
        )

        assert result.ranked_candidates == ()
        assert result.total_excluded == 1

    def test_uses_content_score_as_first_tie_breaker(self):
        first = make_candidate("First")
        second = make_candidate("Second")

        result = self.pipeline.execute(
            candidates=(first, second),
            score_results={
                first.resource_id: make_score(
                    first.resource_id,
                    0.80,
                    relevance=0.60,
                    quality=0.90,
                ),
                second.resource_id: make_score(
                    second.resource_id,
                    0.80,
                    relevance=0.90,
                    quality=0.50,
                ),
            },
            filtering_results=(
                make_filter(first.resource_id),
                make_filter(second.resource_id),
            ),
        )

        assert result.ranked_candidates[0].resource.title == "Second"

    def test_uses_rule_score_as_second_tie_breaker(self):
        first = make_candidate("First")
        second = make_candidate("Second")

        result = self.pipeline.execute(
            candidates=(first, second),
            score_results={
                first.resource_id: make_score(
                    first.resource_id,
                    0.80,
                    relevance=0.70,
                    quality=0.90,
                ),
                second.resource_id: make_score(
                    second.resource_id,
                    0.80,
                    relevance=0.70,
                    quality=0.60,
                ),
            },
            filtering_results=(
                make_filter(first.resource_id),
                make_filter(second.resource_id),
            ),
        )

        assert result.ranked_candidates[0].resource.title == "First"

    def test_applies_limit(self):
        candidates = tuple(
            make_candidate(f"Resource {index}")
            for index in range(5)
        )

        result = self.pipeline.execute(
            candidates=candidates,
            score_results={
                candidate.resource_id: make_score(
                    candidate.resource_id,
                    0.50,
                )
                for candidate in candidates
            },
            filtering_results=tuple(
                make_filter(candidate.resource_id)
                for candidate in candidates
            ),
            limit=2,
        )

        assert len(result.ranked_candidates) == 2

    def test_rejects_invalid_limit(self):
        with pytest.raises(HybridRankingError):
            self.pipeline.execute(
                candidates=(),
                score_results={},
                filtering_results=(),
                limit=0,
            )

    def test_rejects_missing_score(self):
        candidate = make_candidate()

        with pytest.raises(HybridRankingError):
            self.pipeline.execute(
                candidates=(candidate,),
                score_results={},
                filtering_results=(
                    make_filter(candidate.resource_id),
                ),
            )

    def test_rejects_missing_filter_result(self):
        candidate = make_candidate()

        with pytest.raises(HybridRankingError):
            self.pipeline.execute(
                candidates=(candidate,),
                score_results={
                    candidate.resource_id: make_score(
                        candidate.resource_id,
                        0.50,
                    )
                },
                filtering_results=(),
            )

    def test_rejects_duplicate_candidate_ids(self):
        resource_id = uuid4()

        first = make_candidate(
            "First",
            resource_id,
        )

        second = make_candidate(
            "Second",
            resource_id,
        )

        with pytest.raises(HybridRankingError):
            self.pipeline.execute(
                candidates=(first, second),
                score_results={
                    resource_id: make_score(
                        resource_id,
                        0.50,
                    )
                },
                filtering_results=(
                    make_filter(resource_id),
                ),
            )