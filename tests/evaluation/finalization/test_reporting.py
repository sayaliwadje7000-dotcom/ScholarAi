import json

from app.evaluation.finalization.reporting import (
    FinalEvaluationReporter,
)
from app.evaluation.finalization.schemas import (
    EvaluationCheckResult,
    FinalEvaluationReport,
    FinalEvaluationStatus,
)


def create_report():
    result = EvaluationCheckResult(
        check_name="rag_quality",
        category="rag",
        status=FinalEvaluationStatus.PASSED,
        message="RAG evaluation passed.",
        metrics={"score": 0.92},
    )

    return FinalEvaluationReport(
        report_id="test-report",
        status=FinalEvaluationStatus.PASSED,
        total_checks=1,
        passed_checks=1,
        failed_checks=0,
        partial_checks=0,
        not_run_checks=0,
        success_rate=100.0,
        results=[result],
        summary="One evaluation passed.",
    )


def test_report_to_dict():
    report = create_report()

    data = FinalEvaluationReporter.to_dict(report)

    assert data["report_id"] == "test-report"
    assert data["status"] == "passed"


def test_report_to_json():
    report = create_report()

    output = FinalEvaluationReporter.to_json(report)
    parsed = json.loads(output)

    assert parsed["total_checks"] == 1
    assert parsed["results"][0]["check_name"] == "rag_quality"


def test_report_to_text():
    report = create_report()

    output = FinalEvaluationReporter.to_text(report)

    assert "SCHOLARAI FINAL EVALUATION REPORT" in output
    assert "rag_quality" in output
    assert "PASSED" in output


def test_save_json(tmp_path):
    report = create_report()
    destination = tmp_path / "reports" / "final.json"

    saved_path = FinalEvaluationReporter.save_json(
        report,
        destination,
    )

    assert saved_path.exists()

    parsed = json.loads(saved_path.read_text(encoding="utf-8"))
    assert parsed["report_id"] == "test-report"


def test_save_text(tmp_path):
    report = create_report()
    destination = tmp_path / "reports" / "final.txt"

    saved_path = FinalEvaluationReporter.save_text(
        report,
        destination,
    )

    assert saved_path.exists()
    assert "One evaluation passed." in saved_path.read_text(
        encoding="utf-8"
    )
