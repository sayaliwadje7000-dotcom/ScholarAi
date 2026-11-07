from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.services.opportunities.validity.eligibility_evaluator import (
    EligibilityEvaluation,
    OpportunityEligibilityEvaluator,
)

from app.services.opportunities.validity.deadline_evaluator import (
    DeadlineEvaluation,
    OpportunityDeadlineEvaluator,
)

from app.services.opportunities.validity.freshness_evaluator import (
    FreshnessEvaluation,
    OpportunityFreshnessEvaluator,
)


@dataclass(frozen=True)
class OpportunityValidityResult:
    eligibility: EligibilityEvaluation
    deadline: DeadlineEvaluation
    freshness: FreshnessEvaluation

    is_valid_for_registration: bool
    is_displayable: bool
    requires_refresh: bool

    reasons: tuple[str, ...]


class OpportunityValidityService:
    """
    Coordinates opportunity eligibility, deadline and freshness checks.
    """

    def __init__(
        self,
        eligibility_evaluator: OpportunityEligibilityEvaluator | None = None,
        deadline_evaluator: OpportunityDeadlineEvaluator | None = None,
        freshness_evaluator: OpportunityFreshnessEvaluator | None = None,
    ):

        self.eligibility_evaluator = (
            eligibility_evaluator
            or OpportunityEligibilityEvaluator()
        )

        self.deadline_evaluator = (
            deadline_evaluator
            or OpportunityDeadlineEvaluator()
        )

        self.freshness_evaluator = (
            freshness_evaluator
            or OpportunityFreshnessEvaluator()
        )

    def evaluate(
        self,
        opportunity: dict[str, Any],
        student_profile: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> OpportunityValidityResult:

        if not isinstance(opportunity, dict):
            raise ValueError(
                "opportunity must be a dictionary."
            )

        opportunity_type = opportunity.get("opportunity_type")

        if not opportunity_type:
            raise ValueError(
                "Opportunity type is required."
            )

        eligibility = self.eligibility_evaluator.evaluate(
            eligibility=opportunity.get("eligibility", {}),
            student_profile=student_profile,
        )

        deadline = self.deadline_evaluator.evaluate(
            registration_start=opportunity.get(
                "registration_start"
            ),
            registration_deadline=opportunity.get(
                "registration_deadline"
            ),
            event_start=opportunity.get("event_start"),
            event_end=opportunity.get("event_end"),
            current_status=opportunity.get(
                "status",
                "unknown",
            ),
            now=now,
        )

        freshness = self.freshness_evaluator.evaluate(
            opportunity_type=opportunity_type,
            retrieved_at=opportunity.get("retrieved_at"),
            now=now,
        )

        is_valid_for_registration = (
            deadline.registration_open
            and eligibility.status != "not_eligible"
            and opportunity.get("is_active", True)
        )

        is_displayable = (
            opportunity.get("is_active", True)
            and deadline.status not in {
                "expired",
                "cancelled",
            }
        )

        reasons = []

        reasons.extend(eligibility.reasons)
        reasons.extend(deadline.reasons)
        reasons.extend(freshness.reasons)

        if not opportunity.get("is_active", True):
            reasons.append(
                "Opportunity is inactive."
            )

        if eligibility.status == "unknown":
            reasons.append(
                "Student eligibility could not be fully determined."
            )

        if freshness.requires_refresh:
            reasons.append(
                "Opportunity should be refreshed before being treated as current."
            )

        return OpportunityValidityResult(
            eligibility=eligibility,
            deadline=deadline,
            freshness=freshness,
            is_valid_for_registration=is_valid_for_registration,
            is_displayable=is_displayable,
            requires_refresh=freshness.requires_refresh,
            reasons=tuple(reasons),
        )