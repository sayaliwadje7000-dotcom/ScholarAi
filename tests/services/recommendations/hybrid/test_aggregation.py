from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.hybrid.aggregation import (
    CandidateAggregationError,
    CandidateIdentityError,
    CandidateScoreConflictError,
    CandidateURLNormalizer,
    HybridCandidateAggregator,
)

from app.services.recommendations.hybrid.contracts import (
    ComponentScore,
    ComponentStatus,
    HybridCandidate,
    RecommendationComponent,
    RecommendationProvenance,
    ScoreDirection,
)


def make_score(
    component=RecommendationComponent.RULE_BASED,
    value=0.8,
    status=ComponentStatus.AVAILABLE,
    direction=ScoreDirection.HIGHER_IS_BETTER,
):
    return ComponentScore(
        component=component,
        status=status,
        value=value if status == ComponentStatus.AVAILABLE else None,
        direction=direction,
    )


def make_provenance(
    component=RecommendationComponent.RULE_BASED,
    source_name="test-source",
    source_id="resource-1",
    source_url="https://example.com",
):
    return RecommendationProvenance(
        component=component,
        source_name=source_name,
        source_id=source_id,
        source_url=source_url,
        retrieved_at=datetime(
            2026, 11, 9, tzinfo=timezone.utc
        ),
    )


def make_candidate(
    resource_id=None,
    title="Test resource",
    url="https://example.com/resource",
    component_scores=None,
    provenance=None,
    metadata=None,
    description="Test description",
    resource_type="article",
):
    return HybridCandidate(
        resource_id=resource_id or uuid4(),
        title=title,
        resource_type=resource_type,
        component_scores=tuple(
            component_scores or ()
        ),
        provenance=tuple(
            provenance or ()
        ),
        canonical_url=url,
        description=description,
        metadata=metadata or {},
        discovered_at=datetime(
            2026, 11, 9, tzinfo=timezone.utc
        ),
    )


class TestCandidateURLNormalizer:

    def test_normalizes_hostname_case(self):
        result = CandidateURLNormalizer.normalize(
            "HTTPS://EXAMPLE.COM/Resource"
        )

        assert result == "https://example.com/Resource"

    def test_removes_default_https_port(self):
        result = CandidateURLNormalizer.normalize(
            "https://example.com:443/resource"
        )

        assert result == "https://example.com/resource"

    def test_removes_default_http_port(self):
        result = CandidateURLNormalizer.normalize(
            "http://example.com:80/resource"
        )

        assert result == "http://example.com/resource"

    def test_removes_trailing_slash(self):
        result = CandidateURLNormalizer.normalize(
            "https://example.com/resource/"
        )

        assert result == "https://example.com/resource"

    def test_removes_fragment(self):
        result = CandidateURLNormalizer.normalize(
            "https://example.com/resource#section"
        )

        assert result == "https://example.com/resource"

    def test_removes_tracking_parameters(self):
        result = CandidateURLNormalizer.normalize(
            "https://example.com/resource?utm_source=test&id=5"
        )

        assert result == "https://example.com/resource?id=5"

    def test_sorts_query_parameters(self):
        result = CandidateURLNormalizer.normalize(
            "https://example.com/resource?z=2&a=1"
        )

        assert result == "https://example.com/resource?a=1&z=2"

    def test_none_url_returns_none(self):
        assert CandidateURLNormalizer.normalize(None) is None

    def test_empty_url_returns_none(self):
        assert CandidateURLNormalizer.normalize(" ") is None

    def test_rejects_unsupported_scheme(self):
        with pytest.raises(CandidateIdentityError):
            CandidateURLNormalizer.normalize(
                "ftp://example.com/resource"
            )

    def test_rejects_missing_hostname(self):
        with pytest.raises(CandidateIdentityError):
            CandidateURLNormalizer.normalize(
                "https:///resource"
            )


class TestHybridCandidateAggregator:

    def setup_method(self):
        self.aggregator = HybridCandidateAggregator()

    def test_empty_input_returns_empty_result(self):
        result = self.aggregator.aggregate([])

        assert result.candidates == ()
        assert result.input_count == 0
        assert result.output_count == 0
        assert result.duplicate_count == 0

    def test_single_candidate_is_preserved(self):
        candidate = make_candidate()

        result = self.aggregator.aggregate(
            [[candidate]]
        )

        assert result.output_count == 1
        assert result.duplicate_count == 0
        assert result.candidates[0].resource_id == candidate.resource_id

    def test_different_candidates_are_preserved(self):
        first = make_candidate(
            url="https://example.com/one"
        )

        second = make_candidate(
            url="https://example.com/two"
        )

        result = self.aggregator.aggregate(
            [[first, second]]
        )

        assert result.output_count == 2

    def test_same_uuid_candidates_are_merged(self):
        resource_id = uuid4()

        first = make_candidate(
            resource_id=resource_id,
            url="https://example.com/one",
        )

        second = make_candidate(
            resource_id=resource_id,
            url="https://example.com/two",
        )

        result = self.aggregator.aggregate(
            [[first], [second]]
        )

        assert result.output_count == 1
        assert result.duplicate_count == 1

    def test_same_canonical_url_candidates_are_merged(self):
        first = make_candidate(
            url="https://example.com/resource/"
        )

        second = make_candidate(
            url="https://EXAMPLE.com/resource"
        )

        result = self.aggregator.aggregate(
            [[first], [second]]
        )

        assert result.output_count == 1
        assert result.duplicate_count == 1

    def test_tracking_parameters_do_not_prevent_deduplication(self):
        first = make_candidate(
            url="https://example.com/resource?utm_source=a"
        )

        second = make_candidate(
            url="https://example.com/resource?utm_source=b"
        )

        result = self.aggregator.aggregate(
            [[first], [second]]
        )

        assert result.output_count == 1

    def test_uuid_and_url_matches_are_transitive(self):
        shared_id = uuid4()

        first = make_candidate(
            resource_id=shared_id,
            url="https://example.com/first",
        )

        second = make_candidate(
            url="https://example.com/first"
        )

        third = make_candidate(
            resource_id=second.resource_id,
            url="https://example.com/third",
        )

        result = self.aggregator.aggregate(
            [[first], [second], [third]]
        )

        assert result.output_count == 1
        assert result.duplicate_count == 2

    def test_invalid_candidate_type_is_rejected(self):
        with pytest.raises(CandidateAggregationError):
            self.aggregator.aggregate(
                [["invalid"]]
            )

    def test_none_collection_is_rejected(self):
        with pytest.raises(CandidateAggregationError):
            self.aggregator.aggregate(None)

    def test_none_inner_collection_is_rejected(self):
        with pytest.raises(CandidateAggregationError):
            self.aggregator.aggregate(
                [[make_candidate()], None]
            )

    def test_component_scores_are_merged(self):
        resource_id = uuid4()

        first = make_candidate(
            resource_id=resource_id,
            component_scores=[
                make_score(
                    RecommendationComponent.RULE_BASED,
                    0.7,
                )
            ],
        )

        second = make_candidate(
            resource_id=resource_id,
            component_scores=[
                make_score(
                    RecommendationComponent.CONTENT_BASED,
                    0.9,
                )
            ],
        )

        result = self.aggregator.aggregate(
            [[first], [second]]
        )

        merged = result.candidates[0]

        components = {
            score.component
            for score in merged.component_scores
        }

        assert components == {
            RecommendationComponent.RULE_BASED,
            RecommendationComponent.CONTENT_BASED,
        }

    def test_conflicting_available_scores_are_rejected(self):
        resource_id = uuid4()

        first = make_candidate(
            resource_id=resource_id,
            component_scores=[
                make_score(value=0.5)
            ],
        )

        second = make_candidate(
            resource_id=resource_id,
            component_scores=[
                make_score(value=0.9)
            ],
        )

        with pytest.raises(CandidateScoreConflictError):
            self.aggregator.aggregate(
                [[first], [second]]
            )

    def test_available_score_is_preferred_over_unavailable(self):
        resource_id = uuid4()

        first = make_candidate(
            resource_id=resource_id,
            component_scores=[
                make_score(
                    status=ComponentStatus.UNAVAILABLE,
                    value=None,
                )
            ],
        )

        second = make_candidate(
            resource_id=resource_id,
            component_scores=[
                make_score(value=0.8)
            ],
        )

        result = self.aggregator.aggregate(
            [[first], [second]]
        )

        merged_score = result.candidates[0].component_scores[0]

        assert merged_score.status == ComponentStatus.AVAILABLE
        assert merged_score.value == 0.8

    def test_provenance_is_preserved(self):
        resource_id = uuid4()

        first = make_candidate(
            resource_id=resource_id,
            provenance=[
                make_provenance(
                    source_name="rule-engine"
                )
            ],
        )

        second = make_candidate(
            resource_id=resource_id,
            provenance=[
                make_provenance(
                    component=RecommendationComponent.CONTENT_BASED,
                    source_name="content-engine",
                )
            ],
        )

        result = self.aggregator.aggregate(
            [[first], [second]]
        )

        assert len(result.candidates[0].provenance) == 2

    def test_duplicate_provenance_is_removed(self):
        resource_id = uuid4()

        provenance = make_provenance()

        first = make_candidate(
            resource_id=resource_id,
            provenance=[provenance],
        )

        second = make_candidate(
            resource_id=resource_id,
            provenance=[provenance],
        )

        result = self.aggregator.aggregate(
            [[first], [second]]
        )

        assert len(result.candidates[0].provenance) == 1

    def test_metadata_is_merged(self):
        resource_id = uuid4()

        first = make_candidate(
            resource_id=resource_id,
            metadata={"topic": "Python"},
        )

        second = make_candidate(
            resource_id=resource_id,
            metadata={"difficulty": "beginner"},
        )

        result = self.aggregator.aggregate(
            [[first], [second]]
        )

        metadata = result.candidates[0].metadata

        assert metadata["topic"] == "Python"
        assert metadata["difficulty"] == "beginner"

    def test_metadata_conflicts_are_preserved(self):
        resource_id = uuid4()

        first = make_candidate(
            resource_id=resource_id,
            metadata={"difficulty": "beginner"},
        )

        second = make_candidate(
            resource_id=resource_id,
            metadata={"difficulty": "advanced"},
        )

        result = self.aggregator.aggregate(
            [[first], [second]]
        )

        metadata = result.candidates[0].metadata

        assert metadata["difficulty"] == "beginner"

        assert metadata["metadata_conflicts"]["difficulty"] == (
            "beginner",
            "advanced",
        )

    def test_duplicate_count_is_correct(self):
        first = make_candidate(
            url="https://example.com/same"
        )

        second = make_candidate(
            url="https://example.com/same/"
        )

        third = make_candidate(
            url="https://example.com/unique"
        )

        result = self.aggregator.aggregate(
            [[first, second], [third]]
        )

        assert result.input_count == 3
        assert result.output_count == 2
        assert result.duplicate_count == 1

    def test_results_are_deterministically_sorted(self):
        first = make_candidate(
            title="Zebra",
            url="https://example.com/z",
        )

        second = make_candidate(
            title="Apple",
            url="https://example.com/a",
        )

        result = self.aggregator.aggregate(
            [[first, second]]
        )

        titles = [
            candidate.title
            for candidate in result.candidates
        ]

        assert titles == ["Apple", "Zebra"]