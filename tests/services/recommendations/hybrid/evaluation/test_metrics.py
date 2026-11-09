import pytest

from app.services.recommendations.hybrid.evaluation import (
    EvaluationQuery,
    EvaluationDataError,
    EvaluationConfigurationError,
    RecommendationEvaluator,
    RankingConsistencyEvaluator,
)


def test_precision_at_k():

    evaluator = RecommendationEvaluator(k=3)

    relevance = {
        "a": 3,
        "b": 2,
        "c": 1,
        "d": 0,
    }

    ranking = ["a", "d", "b"]

    assert evaluator.precision_at_k(
        ranking,
        relevance,
    ) == pytest.approx(2 / 3)


def test_recall_at_k():

    evaluator = RecommendationEvaluator(k=3)

    relevance = {
        "a": 3,
        "b": 2,
        "c": 1,
        "d": 0,
    }

    ranking = ["a", "b", "d"]

    assert evaluator.recall_at_k(
        ranking,
        relevance,
    ) == pytest.approx(2 / 3)


def test_ndcg_at_k_for_ideal_ranking():

    evaluator = RecommendationEvaluator(k=3)

    relevance = {
        "a": 3,
        "b": 2,
        "c": 1,
    }

    ranking = ["a", "b", "c"]

    assert evaluator.ndcg_at_k(
        ranking,
        relevance,
    ) == pytest.approx(1.0)


def test_duplicate_rate():

    evaluator = RecommendationEvaluator(k=3)

    assert evaluator.duplicate_rate(
        ["a", "b", "a", "c"]
    ) == pytest.approx(0.25)


def test_coverage():

    evaluator = RecommendationEvaluator(k=3)

    catalog = frozenset(
        {"a", "b", "c", "d"}
    )

    assert evaluator.coverage(
        ["a", "b"],
        catalog,
    ) == pytest.approx(0.5)


def test_empty_ranking():

    evaluator = RecommendationEvaluator(k=3)

    result = evaluator.evaluate(
        ranking=[],
        relevance={"a": 3},
    )

    assert result.precision_at_k == 0.0
    assert result.recall_at_k == 0.0
    assert result.ndcg_at_k == 0.0


def test_invalid_k_is_rejected():

    with pytest.raises(EvaluationConfigurationError):

        RecommendationEvaluator(k=0)


def test_invalid_relevance_is_rejected():

    with pytest.raises(EvaluationDataError):

        EvaluationQuery(
            query_id="invalid",
            relevance={
                "resource_1": 5,
            },
        )


def test_ranking_consistency_perfect_agreement():

    result = RankingConsistencyEvaluator.compare(
        ["a", "b", "c"],
        ["a", "b", "c"],
    )

    assert result.agreement == pytest.approx(1.0)


def test_ranking_consistency_complete_disagreement():

    result = RankingConsistencyEvaluator.compare(
        ["a", "b", "c"],
        ["c", "b", "a"],
    )

    assert result.agreement == pytest.approx(0.0)


def test_ranking_consistency_no_shared_resources():

    result = RankingConsistencyEvaluator.compare(
        ["a", "b"],
        ["c", "d"],
    )

    assert result.agreement == 0.0
    assert result.comparable_pairs == 0