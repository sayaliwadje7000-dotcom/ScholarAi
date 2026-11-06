import pytest

from app.services.recommendations.evaluation_metrics import (
    precision_at_k,
    recall_at_k,
    hit_rate_at_k,
    reciprocal_rank,
    ndcg_at_k,
    catalog_coverage,
    intra_list_diversity,
)


def test_precision_at_k():
    recommended = ["a", "b", "c", "d"]
    relevant = {"a", "c"}

    assert precision_at_k(
        recommended,
        relevant,
        4,
    ) == pytest.approx(0.5)


def test_recall_at_k():
    recommended = ["a", "b", "c"]
    relevant = {"a", "c", "e"}

    assert recall_at_k(
        recommended,
        relevant,
        3,
    ) == pytest.approx(2 / 3)


def test_hit_rate_at_k():
    assert hit_rate_at_k(
        ["a", "b", "c"],
        {"c"},
        3,
    ) == 1.0


def test_hit_rate_returns_zero_when_no_relevant_result():
    assert hit_rate_at_k(
        ["a", "b"],
        {"c"},
        2,
    ) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(
        ["a", "b", "c"],
        {"c"},
    ) == pytest.approx(1 / 3)


def test_reciprocal_rank_returns_zero_when_no_match():
    assert reciprocal_rank(
        ["a", "b"],
        {"c"},
    ) == 0.0


def test_ndcg_at_k():
    recommended = ["a", "b", "c"]
    relevant = {"a", "c"}

    result = ndcg_at_k(
        recommended,
        relevant,
        3,
    )

    assert 0.0 <= result <= 1.0


def test_ndcg_perfect_ranking():
    assert ndcg_at_k(
        ["a", "b"],
        {"a", "b"},
        2,
    ) == pytest.approx(1.0)


def test_catalog_coverage():
    recommended = ["a", "b", "c"]
    catalog = {"a", "b", "c", "d", "e"}

    assert catalog_coverage(
        recommended,
        catalog,
    ) == pytest.approx(0.6)


def test_intra_list_diversity():
    categories = {
        "a": {"programming"},
        "b": {"mathematics"},
    }

    result = intra_list_diversity(
        categories,
        ["a", "b"],
    )

    assert result == pytest.approx(1.0)


@pytest.mark.parametrize(
    "metric",
    [
        precision_at_k,
        recall_at_k,
        hit_rate_at_k,
    ],
)
def test_metrics_reject_nonpositive_k(metric):
    with pytest.raises(ValueError):
        metric(["a"], {"a"}, 0)