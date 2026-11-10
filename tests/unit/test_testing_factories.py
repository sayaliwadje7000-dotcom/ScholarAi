from app.evaluation.finalization.schemas import (
    FinalEvaluationStatus,
)
from tests.support.factories import (
    EvaluationReportFactory,
    EvaluationResultFactory,
)


def test_passed_factory_creates_passed_result():
    result = EvaluationResultFactory.passed()

    assert result.status == FinalEvaluationStatus.PASSED
    assert result.check_name == "sample_evaluation"


def test_failed_factory_creates_failed_result():
    result = EvaluationResultFactory.failed()

    assert result.status == FinalEvaluationStatus.FAILED


def test_partial_factory_creates_partial_result():
    result = EvaluationResultFactory.partial()

    assert result.status == FinalEvaluationStatus.PARTIAL


def test_factory_preserves_custom_metrics():
    result = EvaluationResultFactory.passed(
        metrics={"precision": 0.95}
    )

    assert result.metrics["precision"] == 0.95


def test_factory_preserves_custom_details():
    result = EvaluationResultFactory.passed(
        details={"source": "unit_test"}
    )

    assert result.details["source"] == "unit_test"


def test_successful_report_factory():
    report = EvaluationReportFactory.successful(count=4)

    assert report.total_checks == 4
    assert report.passed_checks == 4
    assert report.failed_checks == 0
    assert report.success_rate == 100.0


def test_report_factory_calculates_mixed_results():
    results = [
        EvaluationResultFactory.passed(),
        EvaluationResultFactory.passed(
            check_name="second"
        ),
        EvaluationResultFactory.failed(
            check_name="third"
        ),
    ]

    report = EvaluationReportFactory.create(
        results=results,
        status=FinalEvaluationStatus.FAILED,
    )

    assert report.total_checks == 3
    assert report.passed_checks == 2
    assert report.failed_checks == 1
    assert report.success_rate == 66.67


def test_report_factory_handles_empty_results():
    report = EvaluationReportFactory.create(
        results=[],
        status=FinalEvaluationStatus.NOT_RUN,
    )

    assert report.total_checks == 0
    assert report.success_rate == 0.0


def test_report_factory_preserves_metadata():
    report = EvaluationReportFactory.create(
        metadata={"environment": "testing"}
    )

    assert report.metadata["environment"] == "testing"
