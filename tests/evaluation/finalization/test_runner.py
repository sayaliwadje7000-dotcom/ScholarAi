import pytest

from app.evaluation.finalization.exceptions import (
    EvaluationExecutionError,
)
from app.evaluation.finalization.registry import (
    FinalEvaluationRegistry,
)
from app.evaluation.finalization.runner import (
    FinalEvaluationRunner,
)
from app.evaluation.finalization.schemas import (
    FinalEvaluationStatus,
)


def passed_evaluator():
    return {
        "status": "passed",
        "message": "Evaluation passed.",
        "metrics": {"score": 0.95},
    }


def failed_evaluator():
    return {
        "status": "failed",
        "message": "Evaluation failed.",
    }


def partial_evaluator():
    return {
        "status": "partial",
        "message": "Some checks were unavailable.",
    }


def crashing_evaluator():
    raise RuntimeError("Simulated evaluation failure.")


def test_runner_executes_all_registered_evaluators():
    registry = FinalEvaluationRegistry()
    registry.register("rag", "rag", passed_evaluator)
    registry.register("recommendations", "recommendation", passed_evaluator)

    report = FinalEvaluationRunner(registry).run()

    assert report.total_checks == 2
    assert report.passed_checks == 2
    assert report.status == FinalEvaluationStatus.PASSED


def test_runner_records_failed_evaluator():
    registry = FinalEvaluationRegistry()
    registry.register("rag", "rag", passed_evaluator)
    registry.register("recommendations", "recommendation", failed_evaluator)

    report = FinalEvaluationRunner(registry).run()

    assert report.failed_checks == 1
    assert report.status == FinalEvaluationStatus.FAILED


def test_runner_continues_after_evaluator_exception():
    registry = FinalEvaluationRegistry()
    registry.register("crashing", "rag", crashing_evaluator)
    registry.register("healthy", "rag", passed_evaluator)

    report = FinalEvaluationRunner(registry).run()

    assert report.total_checks == 2
    assert report.failed_checks == 1
    assert report.passed_checks == 1


def test_runner_handles_partial_evaluation():
    registry = FinalEvaluationRegistry()
    registry.register("rag", "rag", partial_evaluator)

    report = FinalEvaluationRunner(registry).run()

    assert report.status == FinalEvaluationStatus.PARTIAL
    assert report.partial_checks == 1


def test_runner_can_select_specific_evaluations():
    registry = FinalEvaluationRegistry()
    registry.register("rag", "rag", passed_evaluator)
    registry.register("recommendations", "recommendation", failed_evaluator)

    report = FinalEvaluationRunner(registry).run(
        selected_evaluations=["rag"]
    )

    assert report.total_checks == 1
    assert report.passed_checks == 1


def test_runner_rejects_unknown_selection():
    registry = FinalEvaluationRegistry()

    with pytest.raises(EvaluationExecutionError):
        FinalEvaluationRunner(registry).run(
            selected_evaluations=["unknown"]
        )


def test_runner_returns_not_run_for_empty_registry():
    registry = FinalEvaluationRegistry()

    report = FinalEvaluationRunner(registry).run()

    assert report.status == FinalEvaluationStatus.NOT_RUN
    assert report.total_checks == 0


def test_runner_preserves_metrics():
    registry = FinalEvaluationRegistry()
    registry.register("rag", "rag", passed_evaluator)

    report = FinalEvaluationRunner(registry).run()

    assert report.results[0].metrics["score"] == 0.95


def test_runner_rejects_invalid_output():
    registry = FinalEvaluationRegistry()

    def invalid_evaluator():
        return "invalid"

    registry.register("invalid", "test", invalid_evaluator)

    report = FinalEvaluationRunner(registry).run()

    assert report.failed_checks == 1
    assert report.results[0].status == FinalEvaluationStatus.FAILED
