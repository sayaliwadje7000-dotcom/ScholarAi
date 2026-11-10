import pytest

from app.evaluation.recommendations.adapters import (
    CallableRecommendationAdapter,
    RecommendationAdapterError,
)
from app.evaluation.recommendations.schemas import RecommendationBenchmarkCase


def make_case():
    return RecommendationBenchmarkCase(
        case_id="case-1",
        user_id="user-1",
        query="AI",
    )


@pytest.mark.asyncio
async def test_sync_pipeline_adapter():
    adapter = CallableRecommendationAdapter(
        lambda **kwargs: [{"id": "resource-1"}]
    )
    result = await adapter.recommend(make_case())
    assert result[0]["item_id"] == "resource-1"


@pytest.mark.asyncio
async def test_async_pipeline_adapter():
    async def pipeline(**kwargs):
        return ["resource-1"]

    adapter = CallableRecommendationAdapter(pipeline)
    result = await adapter.recommend(make_case())
    assert result == [{"item_id": "resource-1"}]


@pytest.mark.asyncio
async def test_invalid_pipeline_output():
    adapter = CallableRecommendationAdapter(
        lambda **kwargs: "invalid"
    )

    with pytest.raises(RecommendationAdapterError):
        await adapter.recommend(make_case())


@pytest.mark.asyncio
async def test_missing_item_id_rejected():
    adapter = CallableRecommendationAdapter(
        lambda **kwargs: [{"title": "Missing ID"}]
    )

    with pytest.raises(RecommendationAdapterError):
        await adapter.recommend(make_case())
