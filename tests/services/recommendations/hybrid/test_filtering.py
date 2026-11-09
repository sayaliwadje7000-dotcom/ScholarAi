from uuid import uuid4

import pytest

from app.services.recommendations.hybrid.filtering import (
    AvailabilityStatus,
    EligibilityDecision,
    FilteringError,
    HybridEligibilityFilter,
    HybridFilteringPipeline,
    UnknownEligibilityPolicy,
)


def make_decision(
    resource_id=None,
    is_valid=True,
    is_eligible=True,
    availability=AvailabilityStatus.AVAILABLE,
):
    return EligibilityDecision(
        resource_id=resource_id or uuid4(),
        is_valid=is_valid,
        is_eligible=is_eligible,
        availability=availability,
    )


class TestHybridEligibilityFilter:

    def test_accepts_valid_eligible_available_resource(self):
        decision = make_decision()

        result = HybridEligibilityFilter().evaluate(
            decision
        )

        assert result.accepted is True
        assert result.exclusion_reasons == ()

    def test_rejects_invalid_resource(self):
        result = HybridEligibilityFilter().evaluate(
            make_decision(is_valid=False)
        )

        assert result.accepted is False
        assert "resource_invalid" in result.exclusion_reasons

    def test_rejects_ineligible_resource(self):
        result = HybridEligibilityFilter().evaluate(
            make_decision(is_eligible=False)
        )

        assert result.accepted is False
        assert "user_not_eligible" in result.exclusion_reasons

    def test_rejects_unavailable_resource(self):
        result = HybridEligibilityFilter().evaluate(
            make_decision(
                availability=AvailabilityStatus.UNAVAILABLE
            )
        )

        assert result.accepted is False

    def test_rejects_expired_resource(self):
        result = HybridEligibilityFilter().evaluate(
            make_decision(
                availability=AvailabilityStatus.EXPIRED
            )
        )

        assert "resource_expired" in result.exclusion_reasons

    def test_unknown_values_are_excluded_by_default(self):
        result = HybridEligibilityFilter().evaluate(
            make_decision(
                is_valid=None,
                is_eligible=None,
                availability=AvailabilityStatus.UNKNOWN,
            )
        )

        assert result.accepted is False
        assert len(result.exclusion_reasons) == 3

    def test_unknown_values_can_be_allowed_with_warnings(self):
        eligibility_filter = HybridEligibilityFilter(
            UnknownEligibilityPolicy.ALLOW_WITH_WARNING
        )

        result = eligibility_filter.evaluate(
            make_decision(
                is_valid=None,
                is_eligible=None,
                availability=AvailabilityStatus.UNKNOWN,
            )
        )

        assert result.accepted is True
        assert len(result.warnings) == 3

    def test_invalid_resource_is_never_allowed_by_unknown_policy(self):
        eligibility_filter = HybridEligibilityFilter(
            UnknownEligibilityPolicy.ALLOW_WITH_WARNING
        )

        result = eligibility_filter.evaluate(
            make_decision(is_valid=False)
        )

        assert result.accepted is False

    def test_rejects_invalid_decision_type(self):
        with pytest.raises(FilteringError):
            HybridEligibilityFilter().evaluate("invalid")


class TestHybridFilteringPipeline:

    def test_processes_multiple_decisions(self):
        first = make_decision()
        second = make_decision(is_eligible=False)

        pipeline = HybridFilteringPipeline(
            HybridEligibilityFilter()
        )

        results = pipeline.execute(
            resource_ids=(
                first.resource_id,
                second.resource_id,
            ),
            decisions={
                first.resource_id: first,
                second.resource_id: second,
            },
        )

        assert len(results) == 2
        assert results[0].accepted is True
        assert results[1].accepted is False

    def test_missing_decision_is_rejected(self):
        first = make_decision()

        pipeline = HybridFilteringPipeline(
            HybridEligibilityFilter()
        )

        with pytest.raises(FilteringError):
            pipeline.execute(
                resource_ids=(first.resource_id,),
                decisions={},
            )

    def test_duplicate_resource_ids_are_rejected(self):
        first = make_decision()

        pipeline = HybridFilteringPipeline(
            HybridEligibilityFilter()
        )

        with pytest.raises(FilteringError):
            pipeline.execute(
                resource_ids=(
                    first.resource_id,
                    first.resource_id,
                ),
                decisions={
                    first.resource_id: first,
                },
            )

    def test_mismatched_decision_id_is_rejected(self):
        first = make_decision()
        second = make_decision()

        pipeline = HybridFilteringPipeline(
            HybridEligibilityFilter()
        )

        with pytest.raises(FilteringError):
            pipeline.execute(
                resource_ids=(first.resource_id,),
                decisions={
                    first.resource_id: second,
                },
            )