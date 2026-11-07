from uuid import uuid4

import pytest

from app.schemas.content_recommendations import (
    ContentRecommendationRequest,
)

from app.services.recommendations.content_based.recommendation_service import (
    ContentBasedRecommendationService,
)


class FakeQueryContextService:

    def build(self, **kwargs):

        return type(
            "FakeContext",
            (),
            {
                "query_embedding": [0.1] * 1536,
            },
        )()


class FakeSimilarityService:

    def find_similar_resources(self, **kwargs):
        return []


class FakeFeatureExtractor:

    def extract(self, resource):
        return None


class FakeScoringService:

    def score(self, **kwargs):
        return None


class FakeFilteringService:

    def filter(self, candidates, criteria):
        return candidates


class FakeRankingService:

    def rank(self, candidates, limit):
        return candidates[:limit]


@pytest.fixture
def recommendation_service():

    return ContentBasedRecommendationService(
        query_context_service=FakeQueryContextService(),
        similarity_service=FakeSimilarityService(),
        feature_extractor=FakeFeatureExtractor(),
        scoring_service=FakeScoringService(),
        filtering_service=FakeFilteringService(),
        ranking_service=FakeRankingService(),
    )


def test_recommendation_service_returns_empty_results(
    recommendation_service,
):

    response = recommendation_service.recommend(
        db=None,
        user_id=uuid4(),
        request=ContentRecommendationRequest(
            query="Learn Python programming",
        ),
    )

    assert response.status == "success"
    assert response.total_results == 0
    assert response.recommendations == []


def test_recommendation_service_preserves_query(
    recommendation_service,
):

    query = "Learn machine learning"

    response = recommendation_service.recommend(
        db=None,
        user_id=uuid4(),
        request=ContentRecommendationRequest(
            query=query,
        ),
    )

    assert response.query == query


def test_recommendation_service_algorithm_version(
    recommendation_service,
):

    response = recommendation_service.recommend(
        db=None,
        user_id=uuid4(),
        request=ContentRecommendationRequest(
            query="Learn Python",
        ),
    )

    assert response.algorithm_version == "content-based-v1"


def test_recommendation_service_rejects_invalid_user(
    recommendation_service,
):

    with pytest.raises(ValueError):

        recommendation_service.recommend(
            db=None,
            user_id="invalid",
            request=ContentRecommendationRequest(
                query="Learn Python",
            ),
        )