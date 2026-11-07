from uuid import uuid4

import pytest

from app.services.recommendations.content_based.evaluation import (
    RecommendationEvaluator,
    RecommendationEvaluationCase,
    RecommendationEvaluationError,
)


@pytest.fixture
def evaluator():
    return RecommendationEvaluator()


def test_perfect_recommendation_metrics(evaluator):

    relevant = {
        "resource-1",
        "resource-2",
        "resource-3",
    }

    result = evaluator.evaluate(
        recommended_ids=[
            "resource-1",
            "resource-2",
            "resource-3",
        ],
        relevant_ids=relevant,
        k=3,
    )

    assert result.precision_at_k == 1.0
    assert result.recall_at_k == 1.0
    assert result.hit_rate_at_k == 1.0
    assert result.reciprocal_rank == 1.0
    assert result.ndcg_at_k == 1.0


def test_no_relevant_recommendations(evaluator):

    result = evaluator.evaluate(
        recommended_ids=[
            "resource-4",
            "resource-5",
        ],
        relevant_ids=[
            "resource-1",
            "resource-2",
        ],
        k=2,
    )

    assert result.precision_at_k == 0.0
    assert result.recall_at_k == 0.0
    assert result.hit_rate_at_k == 0.0
    assert result.reciprocal_rank == 0.0
    assert result.ndcg_at_k == 0.0


def test_precision_uses_k_as_denominator(evaluator):

    result = evaluator.evaluate(
        recommended_ids=[
            "resource-1",
            "resource-2",
        ],
        relevant_ids=[
            "resource-1",
            "resource-2",
        ],
        k=5,
    )

    assert result.precision_at_k == 0.4
    assert result.recall_at_k == 1.0


def test_reciprocal_rank_uses_first_relevant_result(evaluator):

    result = evaluator.evaluate(
        recommended_ids=[
            "resource-1",
            "resource-2",
            "resource-3",
        ],
        relevant_ids=[
            "resource-3",
        ],
        k=3,
    )

    assert result.reciprocal_rank == pytest.approx(
        1 / 3
    )


def test_ndcg_rewards_better_ranking(evaluator):

    relevant = [
        "resource-1",
        "resource-2",
    ]

    better = evaluator.evaluate(
        recommended_ids=[
            "resource-1",
            "resource-2",
            "resource-3",
        ],
        relevant_ids=relevant,
        k=3,
    )

    worse = evaluator.evaluate(
        recommended_ids=[
            "resource-3",
            "resource-1",
            "resource-2",
        ],
        relevant_ids=relevant,
        k=3,
    )

    assert better.ndcg_at_k > worse.ndcg_at_k


def test_duplicate_recommendations_are_removed(evaluator):

    result = evaluator.evaluate(
        recommended_ids=[
            "resource-1",
            "resource-1",
            "resource-2",
        ],
        relevant_ids=[
            "resource-1",
            "resource-2",
        ],
        k=2,
    )

    assert result.precision_at_k == 1.0
    assert result.recall_at_k == 1.0


def test_empty_relevant_set_returns_zero(evaluator):

    result = evaluator.evaluate(
        recommended_ids=[
            "resource-1",
            "resource-2",
        ],
        relevant_ids=[],
        k=2,
    )

    assert result.precision_at_k == 0.0
    assert result.recall_at_k == 0.0
    assert result.hit_rate_at_k == 0.0
    assert result.reciprocal_rank == 0.0
    assert result.ndcg_at_k == 0.0


@pytest.mark.parametrize(
    "invalid_k",
    [
        0,
        -1,
        1.5,
        True,
        "5",
        None,
    ],
)
def test_invalid_k_is_rejected(
    evaluator,
    invalid_k,
):

    with pytest.raises(
        RecommendationEvaluationError
    ):
        evaluator.evaluate(
            recommended_ids=["resource-1"],
            relevant_ids=["resource-1"],
            k=invalid_k,
        )


def test_invalid_recommendation_ids_are_rejected(evaluator):

    with pytest.raises(
        RecommendationEvaluationError
    ):
        evaluator.evaluate(
            recommended_ids="resource-1",
            relevant_ids=["resource-1"],
        )


def test_unhashable_ids_are_rejected(evaluator):

    with pytest.raises(
        RecommendationEvaluationError
    ):
        evaluator.evaluate(
            recommended_ids=[["invalid"]],
            relevant_ids=["resource-1"],
        )


def test_uuid_ids_are_supported(evaluator):

    resource_a = uuid4()
    resource_b = uuid4()

    result = evaluator.evaluate(
        recommended_ids=[
            resource_a,
            resource_b,
        ],
        relevant_ids=[
            resource_a,
        ],
        k=2,
    )

    assert result.precision_at_k == 0.5
    assert result.recall_at_k == 1.0


def test_batch_evaluation(evaluator):

    cases = [
        RecommendationEvaluationCase(
            recommended_ids=(
                "resource-1",
                "resource-2",
            ),
            relevant_ids=frozenset(
                {"resource-1"}
            ),
        ),
        RecommendationEvaluationCase(
            recommended_ids=(
                "resource-3",
                "resource-4",
            ),
            relevant_ids=frozenset(
                {"resource-4"}
            ),
        ),
    ]

    result = evaluator.evaluate_batch(
        cases=cases,
        k=2,
    )

    assert result.query_count == 2

    assert result.mean_precision_at_k == pytest.approx(
        0.5
    )

    assert result.mean_recall_at_k == pytest.approx(
        1.0
    )

    assert result.mean_hit_rate_at_k == 1.0

    assert result.mean_reciprocal_rank == pytest.approx(
        0.75
    )


def test_batch_evaluation_rejects_empty_cases(evaluator):

    with pytest.raises(
        RecommendationEvaluationError
    ):
        evaluator.evaluate_batch(
            cases=[],
            k=5,
        )