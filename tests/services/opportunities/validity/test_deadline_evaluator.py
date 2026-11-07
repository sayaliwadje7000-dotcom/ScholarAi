from datetime import datetime, timedelta, timezone

import pytest

from app.services.opportunities.validity import (
    OpportunityDeadlineEvaluator,
)

from app.services.opportunities.validity.exceptions import (
    OpportunityDeadlineError,
)
from datetime import datetime, timedelta, timezone

from app.services.opportunities.validity.deadline_evaluator import (
    OpportunityDeadlineEvaluator,
)


def test_deadline_equal_to_now_is_not_open():
    """
    An opportunity whose deadline is exactly now
    must not be treated as safely open.
    """
    evaluator = OpportunityDeadlineEvaluator()

    now = datetime.now(timezone.utc)

    result = evaluator.evaluate(
        registration_start=now - timedelta(days=5),
        registration_deadline=now,
        now=now,
    )

    assert result.status == "expired"
    assert result.registration_open is False


@pytest.fixture
def evaluator():
    return OpportunityDeadlineEvaluator()


@pytest.fixture
def now():
    return datetime(
        2026, 11, 8, 12, 0,
        tzinfo=timezone.utc,
    )


def test_registration_is_open(evaluator, now):

    result = evaluator.evaluate(
        registration_start=now - timedelta(days=2),
        registration_deadline=now + timedelta(days=5),
        now=now,
    )

    assert result.status == "open"
    assert result.registration_open
    assert not result.deadline_passed


def test_registration_is_upcoming(evaluator, now):

    result = evaluator.evaluate(
        registration_start=now + timedelta(days=2),
        registration_deadline=now + timedelta(days=5),
        now=now,
    )

    assert result.status == "upcoming"
    assert not result.registration_open


def test_passed_deadline_is_expired(evaluator, now):

    result = evaluator.evaluate(
        registration_start=now - timedelta(days=10),
        registration_deadline=now - timedelta(seconds=1),
        now=now,
    )

    assert result.status == "expired"
    assert result.deadline_passed
    assert not result.registration_open


def test_deadline_equal_to_now_is_expired(evaluator, now):

    result = evaluator.evaluate(
        registration_start=now - timedelta(days=1),
        registration_deadline=now,
        now=now,
    )

    assert result.status == "expired"


def test_missing_deadline_is_unknown(evaluator, now):

    result = evaluator.evaluate(
        registration_start=None,
        registration_deadline=None,
        now=now,
    )

    assert result.status == "unknown"
    assert not result.deadline_known


def test_cancelled_opportunity_remains_cancelled(evaluator, now):

    result = evaluator.evaluate(
        registration_start=now - timedelta(days=1),
        registration_deadline=now + timedelta(days=5),
        current_status="cancelled",
        now=now,
    )

    assert result.status == "cancelled"


def test_event_dates_are_independent(evaluator, now):

    result = evaluator.evaluate(
        registration_start=now - timedelta(days=2),
        registration_deadline=now + timedelta(days=5),
        event_start=now + timedelta(days=10),
        event_end=now + timedelta(days=12),
        now=now,
    )

    assert result.status == "open"
    assert result.registration_open
    assert not result.event_started
    assert not result.event_completed


def test_naive_datetime_is_rejected(evaluator, now):

    with pytest.raises(OpportunityDeadlineError):
        evaluator.evaluate(
            registration_start=datetime(2026, 11, 1),
            registration_deadline=now + timedelta(days=5),
            now=now,
        )


def test_invalid_date_order_is_rejected(evaluator, now):

    with pytest.raises(OpportunityDeadlineError):
        evaluator.evaluate(
            registration_start=now + timedelta(days=5),
            registration_deadline=now,
            now=now,
        )


def test_invalid_status_is_rejected(evaluator, now):

    with pytest.raises(OpportunityDeadlineError):
        evaluator.evaluate(
            registration_start=None,
            registration_deadline=None,
            current_status="invalid",
            now=now,
        )


def test_explicitly_closed_opportunity(evaluator, now):

    result = evaluator.evaluate(
        registration_start=None,
        registration_deadline=now + timedelta(days=5),
        current_status="closed",
        now=now,
    )

    assert result.status == "closed"
    assert not result.registration_open