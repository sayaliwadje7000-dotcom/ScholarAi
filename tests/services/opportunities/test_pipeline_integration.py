from datetime import datetime, timedelta, timezone

from app.services.opportunities.normalization.deduplication_service import (
    OpportunityDeduplicationService,
)

from app.services.opportunities.validity.validity_service import (
    OpportunityValidityService,
)

from app.services.opportunities.ranking.ranking_service import (
    OpportunityRankingService,
)


NOW = datetime(
    2026,
    11,
    8,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_opportunity(
    external_id,
    title,
    status="open",
    skills=None,
    deadline=None,
):

    return {
        "provider": "adzuna",
        "external_id": external_id,
        "title": title,
        "description": (
            "A detailed opportunity for students "
            "interested in Python and artificial intelligence. "
            "Participants will work on practical technical projects."
        ),
        "opportunity_type": "internship",
        "organizer": "Example Organization",
        "official_url": (
            "https://example.com/opportunities/"
            + external_id
        ),
        "source_url": "https://example.com",
        "application_url": (
            "https://example.com/apply/"
            + external_id
        ),
        "eligibility": {},
        "required_skills": skills or ["Python"],
        "location": "India",
        "is_remote": True,
        "registration_start": None,
        "registration_deadline": (
            deadline
            or NOW + timedelta(days=30)
        ),
        "event_start": None,
        "event_end": None,
        "status": status,
        "is_active": True,
        "published_at": NOW,
        "retrieved_at": NOW,
        "metadata": {},
    }


def test_deduplication_removes_identical_records():

    first = make_opportunity(
        "101",
        "Python Internship",
    )

    second = make_opportunity(
        "101",
        "Python Internship",
    )

    result = OpportunityDeduplicationService.deduplicate(
        [first, second]
    )

    assert len(result) == 1


def test_validity_service_rejects_expired_opportunity():

    service = OpportunityValidityService()

    opportunity = make_opportunity(
        "102",
        "Expired Python Internship",
        status="expired",
        deadline=NOW - timedelta(days=1),
    )

    result = service.evaluate(
        opportunity=opportunity,
        student_profile={},
        now=NOW,
    )

    assert result.is_valid_for_registration is False


def test_validity_service_accepts_open_opportunity():

    service = OpportunityValidityService()

    opportunity = make_opportunity(
        "103",
        "Open Python Internship",
    )

    result = service.evaluate(
        opportunity=opportunity,
        student_profile={},
        now=NOW,
    )

    assert result.deadline.status == "open"


def test_ranking_excludes_expired_opportunity():

    service = OpportunityRankingService()

    opportunities = [
        make_opportunity(
            "104",
            "Expired Internship",
            status="expired",
            deadline=NOW - timedelta(days=5),
        ),
        make_opportunity(
            "105",
            "Active Internship",
        ),
    ]

    result = service.rank(
        opportunities=opportunities,
        student_profile={
            "skills": ["Python"],
            "interests": ["AI"],
            "opportunity_types": ["internship"],
        },
        query="Python internship",
        limit=10,
        now=NOW,
    )

    titles = [
        item.opportunity["title"]
        for item in result.ranked_opportunities
    ]

    assert "Expired Internship" not in titles

    assert "Active Internship" in titles