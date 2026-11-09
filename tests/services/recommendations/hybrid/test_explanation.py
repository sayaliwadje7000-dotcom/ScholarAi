from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.hybrid.contracts import (
    HybridCandidate,
    RecommendationComponent,
)

from app.services.recommendations.hybrid.explanation import (
    HybridExplanationError,
    HybridExplanationService,
)

from app.services.recommendations.hybrid.filtering import (
    FilteringResult,
)

from app.services.recommendations.hybrid.ranking import (
    HybridRankingPipeline,
)

from app.services.recommendations.hybrid.scoring import (
    ComponentContribution,
    HybridScoreResult,
)


def make_ranked_candidate():

    resource_id = uuid4()

    candidate = HybridCandidate(
        resource_id=resource_id,
        title="Python Fundamentals",
        resource_type="article",
        component_scores=(),
        provenance=(),
        canonical_url="https://example.com/python",
        description="Python study resource",
        metadata={},
        discovered_at=datetime.now(timezone.utc),
    )

    contributions = (
        ComponentContribution(
            component=RecommendationComponent.RULE_BASED,
            normalized_score=0.80,
            configured_weight=0.30,
            effective_weight=0.50,
            weighted_contribution=0.40,
        ),
        ComponentContribution(
            component=RecommendationComponent.CONTENT_BASED,
            normalized_score=0.90,
            configured_weight=0.30,
            effective_weight=0.50,
            weighted_contribution=0.45,
        ),
    )

    score = HybridScoreResult(
        resource_id=resource_id,
        hybrid_score=0.85,
        normalized_scores=(),
        contributions=contributions,
        available_components=(
            RecommendationComponent.RULE_BASED,
            RecommendationComponent.CONTENT_BASED,
        ),
        excluded_components=(),
        configured_weight_total=0.60,
        effective_weight_total=1.0,
    )

    ranked = HybridRankingPipeline().execute(
        candidates=(candidate,),
        score_results={
            resource_id: score,
        },
        filtering_results=(
            FilteringResult(
                resource_id=resource_id,
                accepted=True,
                exclusion_reasons=(),
                warnings=(),
            ),
        ),
    )

    return ranked.ranked_candidates[0]


class TestHybridExplanationService:

    def setup_method(self):
        self.service = HybridExplanationService()

    def test_generates_explanation(self):
        ranked = make_ranked_candidate()

        result = self.service.explain(ranked)

        assert result.resource_id == ranked.resource.resource_id
        assert result.hybrid_score == 0.85
        assert result.rank == 1

    def test_explains_all_components(self):
        ranked = make_ranked_candidate()

        result = self.service.explain(ranked)

        assert len(result.component_explanations) == 2

    def test_explanation_contains_component_names(self):
        ranked = make_ranked_candidate()

        result = self.service.explain(ranked)

        names = {
            item.component
            for item in result.component_explanations
        }

        assert names == {
            "RULE_BASED",
            "CONTENT_BASED",
        }

    def test_summary_contains_resource_title(self):
        ranked = make_ranked_candidate()

        result = self.service.explain(ranked)

        assert "Python Fundamentals" in result.summary

    def test_explanation_contains_effective_weight(self):
        ranked = make_ranked_candidate()

        result = self.service.explain(ranked)

        assert any(
            "50.00%" in item.explanation
            for item in result.component_explanations
        )

    def test_explanation_is_not_generated_from_invalid_input(self):
        with pytest.raises(HybridExplanationError):
            self.service.explain("invalid")

    def test_explain_many(self):
        ranked = make_ranked_candidate()

        results = self.service.explain_many(
            (ranked, ranked)
        )

        assert len(results) == 2