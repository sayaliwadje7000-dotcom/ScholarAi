import pytest

from app.evaluation.recommendations import (
    CallableRecommendationAdapter,
    RecommendationEvaluationRunner,
    RecommendationEvaluationConfig,
    RecommendationBenchmarkCase,
    RecommendationBenchmarkDataset,
)


@pytest.mark.asyncio
async def test_runner_evaluates_recommendations():
    async def pipeline(**kwargs):
        return [
            {"item_id": "resource-1", "tags": ["AI"]},
            {"item_id": "resource-2", "tags": ["Python"]},
        ]

    dataset = RecommendationBenchmarkDataset(
        dataset_name="runner-test",
        cases=[
            RecommendationBenchmarkCase(
                case_id="case-1",
                user_id="user-1",
                query="AI",
                relevant_item_ids=["resource-1"],
                expected_item_ids=["resource-1"],
                user_preference_tags=["AI"],
                item_tags={
                    "resource-1": ["AI"],
                    "resource-2": ["Python"],
                },
                discovery_item_ids=["resource-1", "resource-2"],
            )
        ],
    )

    runner = RecommendationEvaluationRunner(
        CallableRecommendationAdapter(pipeline),
        RecommendationEvaluationConfig(
            k=2,
            minimum_precision=0.5,
            minimum_recall=1.0,
            minimum_ndcg=1.0,
        ),
    )

    report = await runner.evaluate(dataset)

    assert report.total_cases == 1
    assert report.passed_cases == 1
    assert report.pass_rate == 1.0
    assert report.average_metrics["recall_at_k"] == 1.0


@pytest.mark.asyncio
async def test_runner_marks_failed_thresholds():
    adapter = CallableRecommendationAdapter(
        lambda **kwargs: ["irrelevant"]
    )

    dataset = RecommendationBenchmarkDataset(
        dataset_name="failure-test",
        cases=[
            RecommendationBenchmarkCase(
                case_id="case-1",
                user_id="user-1",
                query="AI",
                relevant_item_ids=["relevant"],
            )
        ],
    )

    runner = RecommendationEvaluationRunner(
        adapter,
        RecommendationEvaluationConfig(minimum_recall=0.5),
    )

    report = await runner.evaluate(dataset)

    assert report.failed_cases == 1
    assert "recall_at_k" in report.results[0].failed_checks


@pytest.mark.asyncio
async def test_empty_dataset():
    dataset = RecommendationBenchmarkDataset(
        dataset_name="empty",
        cases=[],
    )

    runner = RecommendationEvaluationRunner(
        CallableRecommendationAdapter(lambda **kwargs: [])
    )

    report = await runner.evaluate(dataset)

    assert report.total_cases == 0
    assert report.pass_rate == 0.0
