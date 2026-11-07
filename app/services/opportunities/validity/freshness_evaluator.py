from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.services.opportunities.validity.exceptions import (
    OpportunityFreshnessError,
)


DEFAULT_REFRESH_INTERVALS = {
    "hackathon": 12,
    "internship": 24,
    "competition": 24,
    "workshop": 12,
    "conference": 24,
    "academic_event": 24,
    "scholarship": 24,
    "other": 24,
}


@dataclass(frozen=True)
class FreshnessEvaluation:
    status: str
    is_fresh: bool
    requires_refresh: bool
    last_retrieved_at: datetime | None
    next_refresh_at: datetime | None
    age: timedelta | None
    refresh_interval: timedelta
    reasons: tuple[str, ...]


class OpportunityFreshnessEvaluator:
    """
    Evaluates opportunity data freshness.

    Freshness measures how recently data was retrieved.
    It does not establish whether the opportunity is genuine.
    """

    def __init__(
        self,
        refresh_intervals: dict[str, int] | None = None,
    ):

        self.refresh_intervals = dict(
            DEFAULT_REFRESH_INTERVALS
        )

        if refresh_intervals:
            for category, hours in refresh_intervals.items():

                if (
                    isinstance(hours, bool)
                    or not isinstance(hours, int)
                    or hours <= 0
                ):
                    raise OpportunityFreshnessError(
                        f"Invalid refresh interval for {category}."
                    )

                self.refresh_intervals[
                    category.casefold()
                ] = hours

    def evaluate(
        self,
        opportunity_type: str,
        retrieved_at: datetime | None,
        now: datetime | None = None,
    ) -> FreshnessEvaluation:

        now = now or datetime.now(timezone.utc)

        self._validate_datetime(now, "now")
        self._validate_datetime(
            retrieved_at,
            "retrieved_at",
        )

        if not isinstance(opportunity_type, str):
            raise OpportunityFreshnessError(
                "opportunity_type must be a string."
            )

        category = opportunity_type.strip().casefold()

        if not category:
            raise OpportunityFreshnessError(
                "opportunity_type cannot be empty."
            )

        refresh_hours = self.refresh_intervals.get(
            category,
            self.refresh_intervals["other"],
        )

        interval = timedelta(hours=refresh_hours)

        if retrieved_at is None:

            return FreshnessEvaluation(
                status="unknown",
                is_fresh=False,
                requires_refresh=True,
                last_retrieved_at=None,
                next_refresh_at=None,
                age=None,
                refresh_interval=interval,
                reasons=(
                    "Retrieval timestamp is unavailable.",
                ),
            )

        age = now - retrieved_at

        if age < timedelta(0):
            raise OpportunityFreshnessError(
                "retrieved_at cannot be in the future."
            )

        next_refresh_at = retrieved_at + interval

        if age >= interval:

            return FreshnessEvaluation(
                status="stale",
                is_fresh=False,
                requires_refresh=True,
                last_retrieved_at=retrieved_at,
                next_refresh_at=next_refresh_at,
                age=age,
                refresh_interval=interval,
                reasons=(
                    "Opportunity data exceeded its refresh interval.",
                ),
            )

        return FreshnessEvaluation(
            status="fresh",
            is_fresh=True,
            requires_refresh=False,
            last_retrieved_at=retrieved_at,
            next_refresh_at=next_refresh_at,
            age=age,
            refresh_interval=interval,
            reasons=(
                "Opportunity data is within its refresh interval.",
            ),
        )

    @staticmethod
    def _validate_datetime(value, field_name):

        if value is None:
            return

        if not isinstance(value, datetime):
            raise OpportunityFreshnessError(
                f"{field_name} must be a datetime."
            )

        if value.tzinfo is None or value.utcoffset() is None:
            raise OpportunityFreshnessError(
                f"{field_name} must be timezone-aware."
            )