from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.api.opportunities import (
    get_opportunity_registry,
    build_opportunity_services,
)


class MockRegistry:

    def list_providers(self):
        return ["adzuna"]


class MockDiscoveryService:

    async def discover(self, request):

        opportunity = SimpleNamespace(
            provider="adzuna",
            external_id="123",
            title="Python Internship",
            description="A Python development internship.",
            opportunity_type="internship",
            organizer="Example Company",
            official_url="https://example.com/internship",
            source_url="https://example.com",
            application_url="https://example.com/apply",
            eligibility={},
            required_skills=["Python"],
            location="Remote",
            is_remote=True,
            registration_start=None,
            registration_deadline=datetime(
                2027,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            event_start=None,
            event_end=None,
            status="open",
            is_active=True,
            published_at=None,
            retrieved_at=datetime.now(timezone.utc),
            metadata={},
        )

        return SimpleNamespace(
            query=request.query,
            total_results=1,
            opportunities=[opportunity],
            providers_requested=["adzuna"],
            providers_searched=["adzuna"],
            providers_failed=[],
            provider_failures=[],
            retrieved_at=datetime.now(timezone.utc),
        )


class MockDeduplicationService:

    def deduplicate(self, opportunities):

        return [
            {
                "provider": "adzuna",
                "external_id": "123",
                "title": "Python Internship",
                "description": "A Python development internship.",
                "opportunity_type": "internship",
                "organizer": "Example Company",
                "official_url": "https://example.com/internship",
                "source_url": "https://example.com",
                "application_url": "https://example.com/apply",
                "eligibility": {},
                "required_skills": ["Python"],
                "location": "Remote",
                "is_remote": True,
                "registration_start": None,
                "registration_deadline": datetime(
                    2027,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
                "event_start": None,
                "event_end": None,
                "status": "open",
                "is_active": True,
                "published_at": None,
                "retrieved_at": datetime.now(timezone.utc),
                "metadata": {},
            }
        ]


class MockRankingService:

    def rank(
        self,
        opportunities,
        student_profile=None,
        query=None,
        limit=None,
        now=None,
    ):

        opportunity = opportunities[0]

        validity = SimpleNamespace(
            eligibility=SimpleNamespace(
                status="unknown"
            ),
            deadline=SimpleNamespace(
                status="open"
            ),
            freshness=SimpleNamespace(
                status="fresh"
            ),
            requires_refresh=False,
        )

        ranked = SimpleNamespace(
            opportunity=opportunity,
            quality=SimpleNamespace(
                score=90.0
            ),
            relevance=SimpleNamespace(
                score=85.0
            ),
            validity=validity,
            final_score=88.5,
            rank=1,
            explanations=(
                "Required skills match.",
            ),
        )

        return SimpleNamespace(
            ranked_opportunities=(ranked,),
            total_received=1,
            total_ranked=1,
            total_excluded=0,
            exclusion_reasons={},
        )


@pytest.fixture
def client(monkeypatch):

    app.dependency_overrides[
        get_opportunity_registry
    ] = lambda request: MockRegistry()

    monkeypatch.setattr(
        "app.api.opportunities.build_opportunity_services",
        lambda registry: (
            MockDiscoveryService(),
            MockDeduplicationService(),
            MockRankingService(),
        ),
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_opportunity_categories(client):

    response = client.get(
        "/api/v1/opportunities/categories"
    )

    assert response.status_code == 200

    data = response.json()

    assert "hackathon" in data["categories"]

    assert "internship" in data["categories"]


def test_opportunity_discovery(client):

    response = client.post(
        "/api/v1/opportunities/discover",
        json={
            "query": "Python internship",
            "providers": ["adzuna"],
            "opportunity_types": ["internship"],
            "limit_per_provider": 20,
            "max_results": 50,
            "ranking_limit": 20,
            "student_profile": {
                "skills": ["Python"],
                "interests": ["software development"],
                "opportunity_types": ["internship"],
                "academic_year": "3",
                "location": "India",
            },
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "Python internship"

    assert data["total_received"] == 1

    assert data["total_ranked"] == 1

    assert data["total_excluded"] == 0

    assert data["providers_searched"] == ["adzuna"]

    assert len(data["opportunities"]) == 1

    assert (
        data["opportunities"][0]["opportunity"]["title"]
        == "Python Internship"
    )

    assert (
        data["opportunities"][0]["final_score"]
        == 88.5
    )


def test_opportunity_discovery_rejects_empty_query(client):

    response = client.post(
        "/api/v1/opportunities/discover",
        json={
            "query": "   ",
        },
    )

    assert response.status_code == 422


def test_opportunity_discovery_rejects_invalid_limit(client):

    response = client.post(
        "/api/v1/opportunities/discover",
        json={
            "query": "Python internship",
            "ranking_limit": 0,
        },
    )

    assert response.status_code == 422


def test_opportunity_discovery_rejects_unknown_fields(client):

    response = client.post(
        "/api/v1/opportunities/discover",
        json={
            "query": "Python internship",
            "unexpected_field": "invalid",
        },
    )

    assert response.status_code == 422