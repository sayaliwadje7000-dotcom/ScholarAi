import pytest

from app.evaluation.recommendations.metrics import (
    precision_at_k,
    recall_at_k,
    hit_rate_at_k,
    reciprocal_rank,
    ndcg_at_k,
    personalization_alignment,
    discovery_relevance,
    intra_list_diversity,
    novelty,
    serendipity,
)


def test_precision_at_k():
    assert precision_at_k(["a", "b", "c"], {"a", "c"}, 3) == pytest.approx(2 / 3)


def test_recall_at_k():
    assert recall_at_k(["a", "b"], {"a", "c"}, 2) == pytest.approx(0.5)


def test_hit_rate_at_k():
    assert hit_rate_at_k(["a", "b"], {"b"}, 2) == 1.0


def test_reciprocal_rank():
    assert reciprocal_rank(["x", "b", "a"], {"a", "b"}) == 0.5


def test_ndcg_at_k():
    assert ndcg_at_k(["a", "b"], {"a", "b"}, 2) == 1.0


def test_invalid_k():
    with pytest.raises(ValueError):
        precision_at_k(["a"], {"a"}, 0)


def test_personalization_alignment():
    result = personalization_alignment(
        ["a", "b"],
        {"a": ["AI", "Python"], "b": ["History"]},
        {"AI", "Python"},
    )
    assert result == pytest.approx(0.5)


def test_discovery_relevance():
    assert discovery_relevance(["a", "b"], {"a", "b"}, {"a"}) == 0.5


def test_intra_list_diversity():
    assert intra_list_diversity(
        ["a", "b"], {"a": ["AI"], "b": ["History"]}
    ) == 1.0


def test_novelty():
    assert novelty(
        ["popular", "rare"],
        {"popular": 1.0, "rare": 0.0},
    ) == 0.5


def test_serendipity():
    assert serendipity(
        ["expected", "surprise"],
        {"expected"},
        {"expected", "surprise"},
    ) == 0.5
