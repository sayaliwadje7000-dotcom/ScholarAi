import time

from datetime import datetime, timedelta, timezone

from app.services.opportunities.ranking.ranking_service import (
    OpportunityRankingService,
)


NOW = datetime.now(timezone.utc)


def make_opportunity(index):

    return {
        "provider": "adzuna",
        "external_id": str(index),
        "title": f"Python Internship {index}",
        "description": (
            "A detailed Python internship opportunity "
            "for students interested in software engineering "
            "and artificial intelligence."
        ),
        "opportunity_type": "internship",
        "organizer": "Example Organization",
        "official_url": (
            f"https://example.com/internship/{index}"
        ),
        "source_url": "https://example.com",
        "application_url": (
            f"https://example.com/apply/{index}"
        ),
        "eligibility": {},
        "required_skills": ["Python"],
        "location": "India",
        "is_remote": True,
        "registration_start": None,
        "registration_deadline": (
            NOW + timedelta(days=30)
        ),
        "event_start": None,
        "event_end": None,
        "status": "open",
        "is_active": True,
        "published_at": NOW,
        "retrieved_at": NOW,
        "metadata": {},
    }


def test_ranking_performance_100_opportunities():

    opportunities = [
        make_opportunity(index)
        for index in range(100)
    ]

    service = OpportunityRankingService()

    start = time.perf_counter()

    result = service.rank(
        opportunities=opportunities,
        student_profile={
            "skills": ["Python"],
            "opportunity_types": ["internship"],
            "interests": ["software"],
        },
        query="Python internship",
        limit=20,
        now=NOW,
    )

    elapsed = time.perf_counter() - start

    assert result.total_received == 100

    assert len(result.ranked_opportunities) <= 20

    print(
        f"Ranking 100 opportunities took "
        f"{elapsed:.4f} seconds."
    )

    assert elapsed < 5.0