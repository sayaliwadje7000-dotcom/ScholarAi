from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.opportunities.validity.exceptions import (
    OpportunityDeadlineError,
)


VALID_STATUSES = {
    "unknown",
    "upcoming",
    "open",
    "closed",
    "expired",
    "cancelled",
}


@dataclass(frozen=True)
class DeadlineEvaluation:
    status: str
    registration_open: bool
    deadline_passed: bool
    deadline_known: bool
    registration_started: bool
    event_started: bool
    event_completed: bool
    evaluated_at: datetime
    reasons: tuple[str, ...]


class OpportunityDeadlineEvaluator:
    """
    Determines registration and event lifecycle state.

    Registration dates and event dates are evaluated separately.
    """

    def evaluate(
        self,
        registration_start: datetime | None,
        registration_deadline: datetime | None,
        event_start: datetime | None = None,
        event_end: datetime | None = None,
        current_status: str = "unknown",
        now: datetime | None = None,
    ) -> DeadlineEvaluation:

        now = now or datetime.now(timezone.utc)

        self._validate_datetime(now, "now")

        self._validate_datetime(
            registration_start,
            "registration_start",
        )

        self._validate_datetime(
            registration_deadline,
            "registration_deadline",
        )

        self._validate_datetime(event_start, "event_start")
        self._validate_datetime(event_end, "event_end")

        if current_status not in VALID_STATUSES:
            raise OpportunityDeadlineError(
                f"Invalid opportunity status: {current_status}"
            )

        if (
            registration_start is not None
            and registration_deadline is not None
            and registration_start > registration_deadline
        ):
            raise OpportunityDeadlineError(
                "Registration start cannot exceed registration deadline."
            )

        if (
            event_start is not None
            and event_end is not None
            and event_start > event_end
        ):
            raise OpportunityDeadlineError(
                "Event start cannot exceed event end."
            )

        reasons = []

        registration_started = (
            registration_start is None
            or now >= registration_start
        )

        deadline_passed = (
            registration_deadline is not None
            and now >= registration_deadline
        )

        event_started = (
            event_start is not None
            and now >= event_start
        )

        event_completed = (
            event_end is not None
            and now >= event_end
        )

        deadline_known = registration_deadline is not None

        if current_status == "cancelled":
            status = "cancelled"
            reasons.append(
                "Opportunity has been marked as cancelled."
            )

        elif current_status == "closed":
            status = "closed"
            reasons.append(
                "Opportunity has been explicitly marked as closed."
            )

        elif deadline_passed:
            status = "expired"
            reasons.append(
                "Registration deadline has passed."
            )

        elif not registration_started:
            status = "upcoming"
            reasons.append(
                "Registration has not started yet."
            )

        elif registration_deadline is not None:
            status = "open"
            reasons.append(
                "Registration is currently within its date window."
            )

        elif current_status == "expired":
            status = "expired"
            reasons.append(
                "Opportunity was previously marked as expired."
            )

        elif current_status == "upcoming":
            status = "upcoming"
            reasons.append(
                "Opportunity is marked as upcoming."
            )

        else:
            status = "unknown"
            reasons.append(
                "Registration deadline is not known."
            )

        registration_open = status == "open"

        return DeadlineEvaluation(
            status=status,
            registration_open=registration_open,
            deadline_passed=deadline_passed,
            deadline_known=deadline_known,
            registration_started=registration_started,
            event_started=event_started,
            event_completed=event_completed,
            evaluated_at=now,
            reasons=tuple(reasons),
        )

    @staticmethod
    def _validate_datetime(value, field_name):

        if value is None:
            return

        if not isinstance(value, datetime):
            raise OpportunityDeadlineError(
                f"{field_name} must be a datetime."
            )

        if value.tzinfo is None or value.utcoffset() is None:
            raise OpportunityDeadlineError(
                f"{field_name} must be timezone-aware."
            )