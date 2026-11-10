from app.evaluation.recommendations.reporting import (
    report_to_dict,
    render_report,
    save_report,
)
from app.evaluation.recommendations.schemas import (
    RecommendationEvaluationReport,
)


def make_report():
    return RecommendationEvaluationReport(
        dataset_name="report-test",
        dataset_version="1.0",
        total_cases=2,
        passed_cases=1,
        failed_cases=1,
        pass_rate=0.5,
        average_metrics={"recall_at_k": 0.75},
        results=[],
    )


def test_report_to_dict():
    result = report_to_dict(make_report())
    assert result["dataset_name"] == "report-test"
    assert result["pass_rate"] == 0.5


def test_render_report():
    result = render_report(make_report())
    assert "report-test" in result
    assert "recall_at_k" in result


def test_save_report(tmp_path):
    path = tmp_path / "reports" / "report.json"
    save_report(make_report(), path)

    assert path.exists()
    assert '"dataset_name": "report-test"' in path.read_text(
        encoding="utf-8"
    )
