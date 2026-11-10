import pytest

from app.evaluation.finalization.exceptions import (
    DuplicateEvaluationError,
    EvaluationNotFoundError,
    InvalidEvaluationError,
)
from app.evaluation.finalization.registry import (
    FinalEvaluationRegistry,
)


def successful_evaluator():
    return {"status": "passed"}


def test_register_evaluator():
    registry = FinalEvaluationRegistry()

    registry.register(
        "rag_quality",
        "rag",
        successful_evaluator,
    )

    assert len(registry) == 1
    assert registry.get_evaluator_names() == ["rag_quality"]


def test_register_duplicate_evaluator():
    registry = FinalEvaluationRegistry()
    registry.register("rag_quality", "rag", successful_evaluator)

    with pytest.raises(DuplicateEvaluationError):
        registry.register("rag_quality", "rag", successful_evaluator)


def test_register_invalid_evaluator():
    registry = FinalEvaluationRegistry()

    with pytest.raises(InvalidEvaluationError):
        registry.register("rag_quality", "rag", None)


def test_register_empty_name():
    registry = FinalEvaluationRegistry()

    with pytest.raises(InvalidEvaluationError):
        registry.register("", "rag", successful_evaluator)


def test_unregister_evaluator():
    registry = FinalEvaluationRegistry()
    registry.register("rag_quality", "rag", successful_evaluator)

    registry.unregister("rag_quality")

    assert len(registry) == 0


def test_unregister_missing_evaluator():
    registry = FinalEvaluationRegistry()

    with pytest.raises(EvaluationNotFoundError):
        registry.unregister("missing")


def test_list_evaluations():
    registry = FinalEvaluationRegistry()
    registry.register("rag_quality", "rag", successful_evaluator)
    registry.register("recommendation_quality", "recommendation", successful_evaluator)

    evaluations = registry.list_evaluations()

    assert len(evaluations) == 2
    assert evaluations[0]["name"] == "rag_quality"
    assert evaluations[1]["category"] == "recommendation"
