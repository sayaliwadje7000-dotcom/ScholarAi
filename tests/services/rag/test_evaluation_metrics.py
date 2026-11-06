import pytest

from app.services.rag.evaluation_metrics import (
    normalize_text,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    token_f1,
    required_term_coverage,
    citation_precision_recall,
    mean,
)


def test_normalize_text():
    assert normalize_text("ScholarAI RAG System!") == [
        "scholarai",
        "rag",
        "system",
    ]


def test_precision_at_k():
    result = precision_at_k(
        ["a", "b", "c"],
        ["a", "c"],
        3,
    )

    assert result == pytest.approx(2 / 3)


def test_precision_at_k_uses_k_denominator():
    result = precision_at_k(
        ["a"],
        ["a"],
        5,
    )

    assert result == pytest.approx(1 / 5)


def test_precision_at_k_rejects_invalid_k():
    with pytest.raises(ValueError):
        precision_at_k(["a"], ["a"], 0)


def test_recall_at_k():
    result = recall_at_k(
        ["a", "b"],
        ["a", "b", "c"],
        2,
    )

    assert result == pytest.approx(2 / 3)


def test_recall_with_empty_expected():
    assert recall_at_k(["a"], [], 5) == 1.0


def test_reciprocal_rank():
    assert reciprocal_rank(
        ["a", "b", "c"],
        ["c"],
    ) == pytest.approx(1 / 3)


def test_reciprocal_rank_missing_result():
    assert reciprocal_rank(
        ["a", "b"],
        ["c"],
    ) == 0.0


def test_token_f1_perfect_match():
    assert token_f1(
        "Artificial intelligence",
        "Artificial intelligence",
    ) == 1.0


def test_token_f1_no_overlap():
    assert token_f1(
        "database",
        "neural network",
    ) == 0.0


def test_token_f1_both_empty():
    assert token_f1("", "") == 1.0


def test_required_term_coverage():
    result = required_term_coverage(
        "Python supports machine learning.",
        ["Python", "machine learning", "database"],
    )

    assert result == pytest.approx(2 / 3)


def test_required_term_coverage_without_terms():
    assert required_term_coverage("Anything", []) == 1.0


def test_citation_precision_recall():
    precision, recall = citation_precision_recall(
        ["S1", "S2", "S3"],
        ["S1", "S2"],
    )

    assert precision == pytest.approx(2 / 3)
    assert recall == 1.0


def test_citation_metrics_when_both_empty():
    assert citation_precision_recall([], []) == (1.0, 1.0)


def test_mean():
    assert mean([1.0, 2.0, 3.0]) == 2.0


def test_mean_empty():
    assert mean([]) == 0.0