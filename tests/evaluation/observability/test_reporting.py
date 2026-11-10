import json

from app.evaluation.observability.reporting import (
    render_report,
    report_to_dict,
    save_report,
)

from app.evaluation.observability.runner import PerformanceEvaluationRunner
from app.evaluation.observability.schemas import PerformanceSample


def make_report():
    samples = [
        PerformanceSample(
            sample_id="sample-1",
            component="llm",
            operation="generate",
            latency_ms=100,
            success=True,
            input_tokens=100,
            output_tokens=200,
            estimated_cost_usd=0.01,
        )
    ]

    return PerformanceEvaluationRunner().evaluate(samples)


def test_report_to_dict():
    report = make_report()

    result = report_to_dict(report)

    assert result["total_requests"] == 1
    assert result["successful_requests"] == 1
    assert result["passed"] is True


def test_render_report():
    result = render_report(make_report())

    assert "SCHOLARAI PERFORMANCE EVALUATION" in result
    assert "LATENCY" in result
    assert "THROUGHPUT" in result
    assert "COST" in result
    assert "PASSED" in result


def test_save_report(tmp_path):
    path = tmp_path / "reports" / "performance.json"

    saved_path = save_report(make_report(), path)

    assert saved_path.exists()

    data = json.loads(saved_path.read_text(encoding="utf-8"))

    assert data["total_requests"] == 1
    assert data["passed"] is True
