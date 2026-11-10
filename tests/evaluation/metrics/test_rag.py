import pytest

from app.evaluation.metrics.rag import (
    context_precision,
    context_recall,
    answer_relevance,
    faithfulness,
    answer_grounding,
)


def test_context_precision():
    assert context_precision(
        [True, True, False, True]
    ) == pytest.approx(0.75)


def test_context_recall():
    assert context_recall(
        retrieved_relevant=3,
        total_relevant=4,
    ) == pytest.approx(0.75)


def test_answer_relevance():
    assert answer_relevance(
        [1, 1, 0, 1]
    ) == pytest.approx(0.75)


def test_faithfulness():
    assert faithfulness(
        supported_claims=8,
        unsupported_claims=2,
    ) == pytest.approx(0.8)


def test_answer_grounding():
    assert answer_grounding(
        answer_claims=["a", "b", "c"],
        supported_claims=["a", "b"],
    ) == pytest.approx(2 / 3)