from datetime import datetime, timedelta, timezone

from app.services.opportunities.validity import (
    OpportunityValidityService,
)


def test_complete_validity_evaluation():

    now = datetime(
        2026, 11, 8, 12, 0,
        tzinfo=timezone.utc,
    )

    opportunity = {
        "opportunity_type": "internship",
        "eligibility": {
            "branches": ["AIDS", "CSE"],
            "academic_years": [3, 4],
        },
        "registration_start": now - timedelta(days=2),
        "registration_deadline": now + timedelta(days=5),
        "event_start": now + timedelta(days=10),
        "event_end": now + timedelta(days=12),
        "retrieved_at": now - timedelta(hours=2),
        "status": "open",
        "is_active": True,
    }

    student_profile = {
        "branch": "AIDS",
        "academic_year": 3,
    }

    service = OpportunityValidityService()

    result = service.evaluate(
        opportunity=opportunity,
        student_profile=student_profile,
        now=now,
    )

    assert result.eligibility.status == "eligible"
    assert result.deadline.status == "open"
    assert result.freshness.status == "fresh"

    assert result.is_valid_for_registration
    assert result.is_displayable
    assert not result.requires_refresh


def test_expired_opportunity_is_not_valid_for_registration():

    now = datetime.now(timezone.utc)

    opportunity = {
        "opportunity_type": "internship",
        "eligibility": {},
        "registration_start": now - timedelta(days=10),
        "registration_deadline": now - timedelta(days=1),
        "retrieved_at": now,
        "status": "open",
        "is_active": True,
    }

    service = OpportunityValidityService()

    result = service.evaluate(
        opportunity=opportunity,
        now=now,
    )

    assert result.deadline.status == "expired"
    assert not result.is_valid_for_registration
    assert not result.is_displayable


def test_ineligible_student_cannot_register():

    now = datetime.now(timezone.utc)

    opportunity = {
        "opportunity_type": "hackathon",
        "eligibility": {
            "branches": ["CSE"]
        },
        "registration_start": now - timedelta(days=1),
        "registration_deadline": now + timedelta(days=5),
        "retrieved_at": now,
        "status": "open",
        "is_active": True,
    }

    service = OpportunityValidityService()

    result = service.evaluate(
        opportunity=opportunity,
        student_profile={
            "branch": "AIDS"
        },
        now=now,
    )

    assert result.eligibility.status == "not_eligible"
    assert not result.is_valid_for_registration
    assert result.is_displayable


def test_unknown_eligibility_does_not_mean_rejected():

    now = datetime.now(timezone.utc)

    opportunity = {
        "opportunity_type": "internship",
        "eligibility": {
            "branches": ["CSE"]
        },
        "registration_start": now - timedelta(days=1),
        "registration_deadline": now + timedelta(days=5),
        "retrieved_at": now,
        "status": "open",
        "is_active": True,
    }

    service = OpportunityValidityService()

    result = service.evaluate(
        opportunity=opportunity,
        student_profile={},
        now=now,
    )

    assert result.eligibility.status == "unknown"
    assert result.is_valid_for_registration


def test_inactive_opportunity_is_not_displayable():

    now = datetime.now(timezone.utc)

    opportunity = {
        "opportunity_type": "internship",
        "eligibility": {},
        "registration_start": now - timedelta(days=1),
        "registration_deadline": now + timedelta(days=5),
        "retrieved_at": now,
        "status": "open",
        "is_active": False,
    }

    service = OpportunityValidityService()

    result = service.evaluate(
        opportunity=opportunity,
        now=now,
    )

    assert not result.is_displayable
    assert not result.is_valid_for_registration


def test_stale_opportunity_requires_refresh():

    now = datetime.now(timezone.utc)

    opportunity = {
        "opportunity_type": "internship",
        "eligibility": {},
        "registration_start": now - timedelta(days=1),
        "registration_deadline": now + timedelta(days=5),
        "retrieved_at": now - timedelta(days=3),
        "status": "open",
        "is_active": True,
    }

    service = OpportunityValidityService()

    result = service.evaluate(
        opportunity=opportunity,
        now=now,
    )

    assert result.freshness.status == "stale"
    assert result.requires_refresh
    assert result.is_valid_for_registration