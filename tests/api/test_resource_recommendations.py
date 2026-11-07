from datetime import datetime, timezone

import pytest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.resource_recommendations import (
    router,
    get_resource_recommendation_service,
)
from app.schemas.educational_resources import (
    EducationalResourceListResponse,
)
from app.services.educational_resources.recommendation_service import (
    ResourceRecommendationService,
)


class FakeRecommendationService:
    def __init__(self, response=None):
        self.response = response
        self.received_request = None

    async def recommend(self, request):
        self.received_request = request
        return self.response


def create_test_response():
    return EducationalResourceListResponse(
        query="machine learning",
        total_results=0,
        resources=[],
        providers_searched=[],
        providers_failed=[],
        retrieved_at=datetime.now(timezone.utc),
    )

@pytest.fixture
def test_app():
    app = FastAPI()

    fake_service = FakeRecommendationService(
        response=create_test_response()
    )

    app.include_router(
        router,
        prefix="/api/v1",
    )

    app.dependency_overrides[
        get_resource_recommendation_service
    ] = lambda: fake_service

    app.state.fake_recommendation_service = fake_service

    return app


@pytest.mark.asyncio
async def test_recommendation_endpoint_returns_success(
    test_app,
):
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/resources/recommendations",
            json={
                "query": "machine learning",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "machine learning"
    assert data["total_results"] == 0


@pytest.mark.asyncio
async def test_recommendation_endpoint_returns_success(test_app):
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/resources/recommendations",
            json={
                "query": "machine learning",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "machine learning"
    assert data["total_results"] == 0

@pytest.mark.asyncio
async def test_recommendation_service_dependency_missing():
    app = FastAPI()

    app.include_router(
        router,
        prefix="/api/v1",
    )

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/resources/recommendations",
            json={
                "query": "machine learning",
            },
        )

    assert response.status_code == 503


def test_recommendation_service_rejects_none_discovery_service():
    with pytest.raises(ValueError):
        ResourceRecommendationService(
            discovery_service=None
        )