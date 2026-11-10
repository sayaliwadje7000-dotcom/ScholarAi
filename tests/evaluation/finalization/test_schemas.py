import pytest
from pydantic import ValidationError

from app.evaluation.finalization.schemas import (
    EvaluationCheckResult,
    FinalEvaluationReport,
    FinalEvaluationStatus,
)


def test_evaluation_check_result_creation():
    result = EvaluationCheckResult(
        check_name="rag_quality",
        category="rag",
        status=FinalEvaluationStatus.PASSED,
        message="Evaluation successful.",
    )

    assert result.check_name == "rag_quality"
    assert result.status == FinalEvaluationStatus.PASSED


def test_evaluation_check_rejects_empty_name():
    with pytest.raises(ValidationError):
        EvaluationCheckResult(
            check_name="",
            category="rag",
            status=FinalEvaluationStatus.PASSED,
        )


def test_final_report_creation():
    report = FinalEvaluationReport(
        report_id="report-001",
        status=FinalEvaluationStatus.PASSED,
        total_checks=1,
        passed_checks=1,
        failed_checks=0,
        partial_checks=0,
        not_run_checks=0,
        success_rate=100.0,
    )

    assert report.total_checks == 1
    assert report.success_rate == 100.0


def test_final_report_rejects_invalid_success_rate():
    with pytest.raises(ValidationError):
        FinalEvaluationReport(
            report_id="report-001",
            status=FinalEvaluationStatus.PASSED,
            total_checks=1,
            passed_checks=1,
            failed_checks=0,
            partial_checks=0,
            not_run_checks=0,
            success_rate=120.0,
        )
