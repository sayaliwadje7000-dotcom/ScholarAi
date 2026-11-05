import pytest

from app.services.embeddings.retrieval_evaluation import (
    evaluate_retrieval,
    evaluate_retrieval_batch,
)


def test_precision_recall_and_mrr():
    result = evaluate_retrieval(
        retrieved_ids=["A", "B", "C", "D"],
        relevant_ids=["A", "C"],
        k=4,
    )

    assert result.precision_at_k == 0.5
    assert result.recall_at_k == 1.0
    assert result.mean_reciprocal_rank == 1.0
    assert result.relevant_retrieved == 2


def test_mrr_when_first_relevant_result_is_second():
    result = evaluate_retrieval(
        retrieved_ids=["X", "A", "B"],
        relevant_ids=["A"],
        k=3,
    )

    assert result.mean_reciprocal_rank == 0.5


def test_zero_relevant_results():
    result = evaluate_retrieval(
        retrieved_ids=["X", "Y", "Z"],
        relevant_ids=["A"],
        k=3,
    )

    assert result.precision_at_k == 0.0
    assert result.recall_at_k == 0.0
    assert result.mean_reciprocal_rank == 0.0


def test_precision_uses_k_as_denominator():
    result = evaluate_retrieval(
        retrieved_ids=["A"],
        relevant_ids=["A"],
        k=5,
    )

    assert result.precision_at_k == 0.2
    assert result.recall_at_k == 1.0


def test_invalid_k_rejected():
    with pytest.raises(ValueError):
        evaluate_retrieval(["A"], ["A"], k=0)


def test_boolean_k_rejected():
    with pytest.raises(ValueError):
        evaluate_retrieval(["A"], ["A"], k=True)


def test_empty_relevant_ids_rejected():
    with pytest.raises(ValueError):
        evaluate_retrieval(["A"], [], k=5)


def test_duplicate_retrieved_ids_rejected():
    with pytest.raises(ValueError):
        evaluate_retrieval(["A", "A"], ["A"], k=2)


def test_batch_evaluation():
    retrieved = {
        "query_1": ["A", "B", "C"],
        "query_2": ["X", "Y", "Z"],
    }

    relevant = {
        "query_1": ["A"],
        "query_2": ["Y"],
    }

    result = evaluate_retrieval_batch(
        retrieved_by_query=retrieved,
        relevant_by_query=relevant,
        k=3,
    )

    assert result.query_count == 2
    assert result.precision_at_k == pytest.approx(1 / 3)
    assert result.recall_at_k == pytest.approx(1.0)
    assert result.mean_reciprocal_rank == pytest.approx(0.75)


def test_batch_rejects_mismatched_query_ids():
    with pytest.raises(ValueError):
        evaluate_retrieval_batch(
            retrieved_by_query={"query_1": ["A"]},
            relevant_by_query={"query_2": ["A"]},
        )


def test_batch_rejects_empty_input():
    with pytest.raises(ValueError):
        evaluate_retrieval_batch({}, {})