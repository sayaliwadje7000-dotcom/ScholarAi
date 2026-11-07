import pytest

from app.services.opportunities.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    f1_score,
    dcg_at_k,
    ndcg_at_k,
    duplicate_rate,
    expired_leakage_rate,
    eligibility_violation_rate,
    provider_success_rate,
)


def test_precision_at_k():

    relevant = ["A", "B", "C"]

    recommended = ["A", "X", "B", "Y"]

    assert precision_at_k(
        relevant,
        recommended,
        3,
    ) == pytest.approx(2 / 3)


def test_recall_at_k():

    relevant = ["A", "B", "C"]

    recommended = ["A", "X", "B"]

    assert recall_at_k(
        relevant,
        recommended,
        3,
    ) == pytest.approx(2 / 3)


def test_f1_score():

    assert f1_score(
        0.8,
        0.6,
    ) == pytest.approx(
        0.6857142857
    )


def test_f1_score_zero():

    assert f1_score(
        0.0,
        0.0,
    ) == 0.0


def test_dcg_at_k():

    result = dcg_at_k(
        [3, 2, 1],
        3,
    )

    assert result > 0


def test_ndcg_perfect_ranking():

    result = ndcg_at_k(
        [3, 2, 1],
        3,
    )

    assert result == pytest.approx(1.0)


def test_ndcg_reversed_ranking():

    result = ndcg_at_k(
        [1, 2, 3],
        3,
    )

    assert 0 < result < 1


def test_duplicate_rate():

    result = duplicate_rate(
        ["A", "B", "A", "C"]
    )

    assert result == pytest.approx(0.25)


def test_duplicate_rate_no_duplicates():

    result = duplicate_rate(
        ["A", "B", "C"]
    )

    assert result == 0.0


def test_expired_leakage_rate():

    result = expired_leakage_rate(
        [
            "open",
            "expired",
            "upcoming",
            "cancelled",
        ]
    )

    assert result == pytest.approx(0.5)


def test_eligibility_violation_rate():

    result = eligibility_violation_rate(
        [
            "eligible",
            "not_eligible",
            "unknown",
        ]
    )

    assert result == pytest.approx(1 / 3)


def test_provider_success_rate():

    assert provider_success_rate(
        3,
        4,
    ) == pytest.approx(0.75)


def test_provider_success_rate_zero_requested():

    assert provider_success_rate(
        0,
        0,
    ) == 0.0


def test_precision_rejects_invalid_k():

    with pytest.raises(ValueError):

        precision_at_k(
            ["A"],
            ["A"],
            0,
        )


def test_provider_success_rejects_invalid_counts():

    with pytest.raises(ValueError):

        provider_success_rate(
            5,
            3,
        )