import pytest

from app.services.educational_resources.discovery_evaluation import (
    DiscoveryEvaluator,
    RankingMetrics,
)


@pytest.fixture
def ranking():
    return [
        "resource_a",
        "resource_b",
        "resource_c",
        "resource_d",
        "resource_e",
    ]


@pytest.fixture
def relevance():
    return {
        "resource_a": 3,
        "resource_b": 0,
        "resource_c": 2,
        "resource_d": 0,
        "resource_e": 1,
    }


def test_precision_at_k(ranking, relevance):
    result = DiscoveryEvaluator.precision_at_k(
        ranking,
        relevance,
        k=5,
    )

    assert result == pytest.approx(0.6)


def test_recall_at_k(ranking, relevance):
    result = DiscoveryEvaluator.recall_at_k(
        ranking,
        relevance,
        k=5,
    )

    assert result == pytest.approx(1.0)


def test_reciprocal_rank(ranking, relevance):
    result = DiscoveryEvaluator.reciprocal_rank(
        ranking,
        relevance,
        k=5,
    )

    assert result == pytest.approx(1.0)


def test_ndcg_at_k(ranking, relevance):
    result = DiscoveryEvaluator.ndcg_at_k(
        ranking,
        relevance,
        k=5,
    )

    assert 0.0 < result <= 1.0


def test_evaluate_returns_all_metrics(
    ranking,
    relevance,
):
    result = DiscoveryEvaluator.evaluate(
        ranking,
        relevance,
        k=5,
    )

    assert isinstance(result, RankingMetrics)

    assert result.precision_at_k == pytest.approx(0.6)
    assert result.recall_at_k == pytest.approx(1.0)
    assert result.reciprocal_rank == pytest.approx(1.0)

    assert 0.0 <= result.ndcg_at_k <= 1.0


def test_duplicate_resource_ids_are_not_counted_twice():
    ranking = [
        "resource_a",
        "resource_a",
        "resource_b",
    ]

    relevance = {
        "resource_a": 2,
        "resource_b": 0,
    }

    result = DiscoveryEvaluator.precision_at_k(
        ranking,
        relevance,
        k=3,
    )

    assert result == pytest.approx(1 / 3)


def test_empty_ranking_returns_zero():
    relevance = {
        "resource_a": 2,
    }

    assert DiscoveryEvaluator.precision_at_k(
        [],
        relevance,
        k=5,
    ) == 0.0

    assert DiscoveryEvaluator.recall_at_k(
        [],
        relevance,
        k=5,
    ) == 0.0

    assert DiscoveryEvaluator.reciprocal_rank(
        [],
        relevance,
        k=5,
    ) == 0.0


def test_no_relevant_resources_returns_zero():
    ranking = ["resource_a"]

    relevance = {
        "resource_a": 0,
    }

    assert DiscoveryEvaluator.recall_at_k(
        ranking,
        relevance,
        k=5,
    ) == 0.0


def test_invalid_k_is_rejected():
    with pytest.raises(ValueError):
        DiscoveryEvaluator.precision_at_k(
            [],
            {},
            k=0,
        )


def test_invalid_relevance_score_is_rejected():
    with pytest.raises(ValueError):
        DiscoveryEvaluator.evaluate(
            ["resource_a"],
            {
                "resource_a": -1,
            },
        )


def test_non_numeric_relevance_score_is_rejected():
    with pytest.raises(TypeError):
        DiscoveryEvaluator.evaluate(
            ["resource_a"],
            {
                "resource_a": "high",
            },
        )


def test_invalid_resource_identifier_is_rejected():
    with pytest.raises(ValueError):
        DiscoveryEvaluator.evaluate(
            [""],
            {},
        )