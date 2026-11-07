from datetime import datetime, timedelta, timezone

import pytest

from app.services.opportunities.ranking import (
    OpportunityRankingService,
    RankingSettings,
)


@pytest.fixture
def now():
    return datetime(
        2026, 11, 8, 12, 0,
        tzinfo=timezone.utc,
    )


def make_opportunity(
    title,
    now,
    skills=None,
    deadline_days=5,
    status="open",
    branch="AIDS",
):

    return {
        "title": title,
        "description": (
            "A student opportunity involving Python, artificial intelligence "
            "and practical technical projects."
        ),
        "opportunity_type": "internship",
        "provider": "example",
        "external_id": title.casefold().replace(" ", "-"),
        "organizer": "Example Organization",
        "official_url": "https://example.com/opportunity",
        "source_url": "https://example.com/listing",
        "eligibility": {
            "branches": [branch],
        },
        "required_skills": skills or ["Python"],
        "location": "Pune",
        "is_remote": False,
        "registration_start": now - timedelta(days=2),
        "registration_deadline": now + timedelta(days=deadline_days),
        "event_start": None,
        "event_end": None,
        "retrieved_at": now - timedelta(hours=2),
        "status": status,
        "is_active": True,
        "opportunity_metadata": {
            "sources": ["example"],
        },
    }


def test_ranker_returns_results_in_descending_score_order(now):

    opportunities = [
        make_opportunity(
            "Python Internship",
            now,
            skills=["Python"],
        ),
        make_opportunity(
            "Java Internship",
            now,
            skills=["Java"],
        ),
    ]

    service = OpportunityRankingService()

    result = service.rank(
        opportunities=opportunities,
        student_profile={
            "skills": ["Python"],
            "preferred_opportunity_types": ["internship"],
        },
        now=now,
    )

    scores = [
        item.final_score
        for item in result.ranked_opportunities
    ]

    assert scores == sorted(scores, reverse=True)


def test_expired_opportunity_is_excluded(now):

    opportunity = make_opportunity(
        "Expired Internship",
        now,
        deadline_days=-1,
    )

    service = OpportunityRankingService()

    result = service.rank(
        opportunities=[opportunity],
        now=now,
    )

    assert result.total_ranked == 0
    assert result.exclusion_reasons["expired"] == 1


def test_cancelled_opportunity_is_excluded(now):

    opportunity = make_opportunity(
        "Cancelled Internship",
        now,
        status="cancelled",
    )

    service = OpportunityRankingService()

    result = service.rank(
        opportunities=[opportunity],
        now=now,
    )

    assert result.total_ranked == 0
    assert result.exclusion_reasons["cancelled"] == 1


def test_ineligible_student_is_excluded(now):

    opportunity = make_opportunity(
        "CSE Internship",
        now,
        branch="CSE",
    )

    service = OpportunityRankingService()

    result = service.rank(
        opportunities=[opportunity],
        student_profile={
            "branch": "AIDS",
        },
        now=now,
    )

    assert result.total_ranked == 0
    assert result.exclusion_reasons["not_eligible"] == 1


def test_unknown_eligibility_is_retained_by_default(now):

    opportunity = make_opportunity(
        "Internship",
        now,
        branch="CSE",
    )

    service = OpportunityRankingService()

    result = service.rank(
        opportunities=[opportunity],
        student_profile={},
        now=now,
    )

    assert result.total_ranked == 1


def test_unknown_eligibility_can_be_excluded(now):

    opportunity = make_opportunity(
        "Internship",
        now,
        branch="CSE",
    )

    service = OpportunityRankingService(
        settings=RankingSettings(
            exclude_unknown_eligibility=True,
        )
    )

    result = service.rank(
        opportunities=[opportunity],
        student_profile={},
        now=now,
    )

    assert result.total_ranked == 0
    assert result.exclusion_reasons["unknown_eligibility"] == 1


def test_stale_opportunity_can_be_excluded(now):

    opportunity = make_opportunity(
        "Old Internship",
        now,
    )

    opportunity["retrieved_at"] = now - timedelta(days=5)

    service = OpportunityRankingService(
        settings=RankingSettings(
            exclude_stale_opportunities=True,
        )
    )

    result = service.rank(
        opportunities=[opportunity],
        now=now,
    )

    assert result.total_ranked == 0
    assert result.exclusion_reasons["stale"] == 1


def test_limit_is_respected(now):

    opportunities = [
        make_opportunity(f"Internship {index}", now)
        for index in range(5)
    ]

    service = OpportunityRankingService()

    result = service.rank(
        opportunities=opportunities,
        limit=2,
        now=now,
    )

    assert result.total_ranked == 2


def test_rank_numbers_are_sequential(now):

    opportunities = [
        make_opportunity(f"Internship {index}", now)
        for index in range(3)
    ]

    service = OpportunityRankingService()

    result = service.rank(
        opportunities=opportunities,
        now=now,
    )

    ranks = [
        item.rank
        for item in result.ranked_opportunities
    ]

    assert ranks == [1, 2, 3]


def test_inactive_opportunity_is_excluded(now):

    opportunity = make_opportunity(
        "Inactive Internship",
        now,
    )

    opportunity["is_active"] = False

    service = OpportunityRankingService()

    result = service.rank(
        opportunities=[opportunity],
        now=now,
    )

    assert result.total_ranked == 0
    assert result.exclusion_reasons["inactive"] == 1


def test_invalid_limit_is_rejected(now):

    service = OpportunityRankingService()

    with pytest.raises(ValueError):
        service.rank(
            opportunities=[],
            limit=0,
            now=now,
        )


def test_response_contains_explanations(now):

    opportunity = make_opportunity(
        "Python Internship",
        now,
    )

    service = OpportunityRankingService()

    result = service.rank(
        opportunities=[opportunity],
        student_profile={
            "skills": ["Python"],
        },
        now=now,
    )

    assert result.total_received == 1
    assert result.total_ranked == 1
    assert result.total_excluded == 0

    ranked = result.ranked_opportunities[0]

    assert 0 <= ranked.final_score <= 100
    assert len(ranked.explanations) > 0
    assert ranked.rank == 1