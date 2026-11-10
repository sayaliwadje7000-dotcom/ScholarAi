import pytest

from app.evaluation.finalization.aggregation import (
    aggregate_evaluation_results,
)
from app.evaluation.finalization.schemas import (
    EvaluationCheckResult,
    FinalEvaluationStatus,
)


def make_result(name, status):
    return EvaluationCheckResult(
        check_name=name,
        category="test",
        status=status,
    )


def test_all_passed():
    results = [
        make_result("rag", FinalEvaluationStatus.PASSED),
        make_result("recommendations", FinalEvaluationStatus.PASSED),
    ]

    aggregate = aggregate_evaluation_results(results)

    assert aggregate["status"] == FinalEvaluationStatus.PASSED
    assert aggregate["success_rate"] == 100.0


def test_one_failed_means_overall_failure():
    results = [
        make_result("rag", FinalEvaluationStatus.PASSED),
        make_result("recommendations", FinalEvaluationStatus.FAILED),
    ]

    aggregate = aggregate_evaluation_results(results)

    assert aggregate["status"] == FinalEvaluationStatus.FAILED
    assert aggregate["failed_checks"] == 1
    assert aggregate["success_rate"] == 50.0


def test_partial_result_produces_partial_status():
    results = [
        make_result("rag", FinalEvaluationStatus.PASSED),
        make_result("recommendations", FinalEvaluationStatus.PARTIAL),
    ]

    aggregate = aggregate_evaluation_results(results)

    assert aggregate["status"] == FinalEvaluationStatus.PARTIAL


def test_empty_results_are_not_run():
    aggregate = aggregate_evaluation_results([])

    assert aggregate["status"] == FinalEvaluationStatus.NOT_RUN
    assert aggregate["total_checks"] == 0
    assert aggregate["success_rate"] == 0.0


def test_counts_are_accurate():
    results = [
        make_result("a", FinalEvaluationStatus.PASSED),
        make_result("b", FinalEvaluationStatus.FAILED),
        make_result("c", FinalEvaluationStatus.PARTIAL),
        make_result("d", FinalEvaluationStatus.NOT_RUN),
    ]

    aggregate = aggregate_evaluation_results(results)

    assert aggregate["total_checks"] == 4
    assert aggregate["passed_checks"] == 1
    assert aggregate["failed_checks"] == 1
    assert aggregate["partial_checks"] == 1
    assert aggregate["not_run_checks"] == 1
    assert aggregate["success_rate"] == 25.0
