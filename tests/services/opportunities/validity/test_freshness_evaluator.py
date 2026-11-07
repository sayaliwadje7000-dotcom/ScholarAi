from datetime import datetime, timedelta, timezone

import pytest

from app.services.opportunities.validity import (
    OpportunityFreshnessEvaluator,
)

from app.services.opportunities.validity.exceptions import (
    OpportunityFreshnessError,
)


@pytest.fixture
def evaluator():
    return OpportunityFreshnessEvaluator()


@pytest.fixture
def now():
    return datetime(
        2026, 11, 8, 12, 0,
        tzinfo=timezone.utc,
    )


def test_recent_opportunity_is_fresh(evaluator, now):

    result = evaluator.evaluate(
        opportunity_type="internship",
        retrieved_at=now - timedelta(hours=2),
        now=now,
    )

    assert result.status == "fresh"
    assert result.is_fresh
    assert not result.requires_refresh


def test_old_opportunity_is_stale(evaluator, now):

    result = evaluator.evaluate(
        opportunity_type="internship",
        retrieved_at=now - timedelta(hours=30),
        now=now,
    )

    assert result.status == "stale"
    assert not result.is_fresh
    assert result.requires_refresh


def test_missing_timestamp_requires_refresh(evaluator, now):

    result = evaluator.evaluate(
        opportunity_type="hackathon",
        retrieved_at=None,
        now=now,
    )

    assert result.status == "unknown"
    assert result.requires_refresh


def test_hackathon_uses_twelve_hour_interval(evaluator, now):

    result = evaluator.evaluate(
        opportunity_type="hackathon",
        retrieved_at=now - timedelta(hours=13),
        now=now,
    )

    assert result.status == "stale"
    assert result.refresh_interval == timedelta(hours=12)


def test_custom_refresh_interval(now):

    evaluator = OpportunityFreshnessEvaluator(
        refresh_intervals={
            "internship": 6
        }
    )

    result = evaluator.evaluate(
        opportunity_type="internship",
        retrieved_at=now - timedelta(hours=7),
        now=now,
    )

    assert result.status == "stale"
    assert result.refresh_interval == timedelta(hours=6)


def test_future_timestamp_is_rejected(evaluator, now):

    with pytest.raises(OpportunityFreshnessError):
        evaluator.evaluate(
            opportunity_type="internship",
            retrieved_at=now + timedelta(hours=1),
            now=now,
        )


def test_naive_timestamp_is_rejected(evaluator, now):

    with pytest.raises(OpportunityFreshnessError):
        evaluator.evaluate(
            opportunity_type="internship",
            retrieved_at=datetime(2026, 11, 8, 10, 0),
            now=now,
        )


def test_invalid_refresh_interval():

    with pytest.raises(OpportunityFreshnessError):
        OpportunityFreshnessEvaluator(
            refresh_intervals={
                "internship": 0
            }
        )