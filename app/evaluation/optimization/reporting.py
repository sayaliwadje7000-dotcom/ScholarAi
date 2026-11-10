import json
from pathlib import Path

from app.evaluation.optimization.schemas import OptimizationReport


def report_to_dict(report: OptimizationReport) -> dict:
    return report.model_dump(mode="json")


def report_to_json(
    report: OptimizationReport,
    indent: int = 2,
) -> str:
    return json.dumps(
        report_to_dict(report),
        indent=indent,
        allow_nan=False,
    )


def save_report(
    report: OptimizationReport,
    path: str | Path,
) -> Path:
    destination = Path(path)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        report_to_json(report),
        encoding="utf-8",
    )

    return destination


def report_to_text(report: OptimizationReport) -> str:
    lines = [
        "AI QUALITY OPTIMIZATION REPORT",
        "=" * 40,
        f"Optimization ID: {report.optimization_id}",
        f"Completed: {report.completed}",
        f"Passed: {report.passed}",
        "",
        f"Baseline score: {report.baseline_score:.6f}",
        f"Selected candidate: {report.selected_candidate_id or 'None'}",
        f"Selected score: {report.selected_score}",
        f"Improvement: {report.improvement}",
        "",
        "CANDIDATE RESULTS",
        "-" * 40,
    ]

    for evaluation in report.evaluations:
        lines.extend(
            [
                f"Candidate: {evaluation.candidate_id}",
                f"Objective score: {evaluation.objective_score}",
                f"Accepted: {evaluation.accepted}",
                f"Violations: {evaluation.violations}",
                "",
            ]
        )

    lines.append(f"Summary: {report.summary}")

    return "\n".join(lines)
