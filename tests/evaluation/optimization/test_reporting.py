import json

from app.evaluation.optimization.reporting import (
    report_to_dict,
    report_to_json,
    report_to_text,
    save_report,
)
from app.evaluation.optimization.runner import OptimizationRunner
from app.evaluation.optimization.schemas import (
    OptimizationCandidate,
    OptimizationConfig,
)


def create_report():
    config = OptimizationConfig(
        optimization_id="report-test",
        baseline_candidate=OptimizationCandidate(
            candidate_id="baseline"
        ),
        candidates=[
            OptimizationCandidate(candidate_id="candidate-1")
        ],
        objective_metric="quality",
        minimum_samples=1,
    )

    def evaluator(candidate):
        if candidate.candidate_id == "baseline":
            return {"quality": [0.7]}

        return {"quality": [0.9]}

    return OptimizationRunner(config, evaluator).run()


def test_report_to_dict():
    report = create_report()

    result = report_to_dict(report)

    assert result["optimization_id"] == "report-test"
    assert result["passed"] is True


def test_report_to_json():
    report = create_report()

    result = report_to_json(report)
    parsed = json.loads(result)

    assert parsed["selected_candidate_id"] == "candidate-1"


def test_save_report(tmp_path):
    report = create_report()
    destination = tmp_path / "reports" / "optimization.json"

    saved_path = save_report(report, destination)

    assert saved_path.exists()
    assert json.loads(saved_path.read_text())["passed"] is True


def test_report_to_text():
    report = create_report()

    result = report_to_text(report)

    assert "AI QUALITY OPTIMIZATION REPORT" in result
    assert "candidate-1" in result
