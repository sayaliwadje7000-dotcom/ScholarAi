import pytest

from app.evaluation.metrics.ranking import (
    precision_at_k,
    recall_at_k,
    hit_rate_at_k,
    reciprocal_rank,
    mean_reciprocal_rank,
    average_precision,
    mean_average_precision,
    dcg_at_k,
    ndcg_at_k,
)


def test_precision_at_k():
    assert precision_at_k(
        ["a", "b", "c"],
        {"a", "c"},
        2,
    ) == pytest.approx(0.5)


def test_recall_at_k():
    assert recall_at_k(
        ["a", "b", "c"],
        {"a", "c"},
        2,
    ) == pytest.approx(0.5)


def test_hit_rate_at_k():
    assert hit_rate_at_k(
        ["a", "b"],
        {"b"},
        2,
    ) == 1.0


def test_reciprocal_rank():
    assert reciprocal_rank(
        ["x", "b", "a"],
        {"a", "b"},
    ) == pytest.approx(0.5)


def test_mean_reciprocal_rank():
    result = mean_reciprocal_rank(
        [
            ["a", "b"],
            ["x", "b"],
        ],
        [
            {"a"},
            {"b"},
        ],
    )

    assert result == pytest.approx(0.75)


def test_average_precision():
    result = average_precision(
        ["a", "x", "b"],
        {"a", "b"},
    )

    assert result == pytest.approx(5 / 6)


def test_mean_average_precision():
    result = mean_average_precision(
        [
            ["a", "x", "b"],
            ["x", "b", "a"],
        ],
        [
            {"a", "b"},
            {"a", "b"},
        ],
    )

    assert result == pytest.approx(17 / 24)


def test_dcg_at_k():
    result = dcg_at_k([3, 2, 1], 3)

    assert result > 0


def test_ndcg_at_k():
    assert ndcg_at_k([3, 2, 1], 3) == pytest.approx(1.0)