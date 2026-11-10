import json
from pathlib import Path
from typing import Any

from app.evaluation.experiments.schemas import (
    ExperimentComparisonReport,
)


def report_to_dict(
    report: ExperimentComparisonReport,
) -> dict[str, Any]:
    return report.model_dump(mode="json")


def save_report(
    report: ExperimentComparisonReport,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            report_to_dict(report),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return path


def render_report(
    report: ExperimentComparisonReport,
) -> str:
    winner = report.winner or "No statistically established winner"

    lines = [
        f"Experiment: {report.experiment_id}",
        f"Metric: {report.metric_name}",
        "",
        f"Baseline: {report.baseline_variant}",
        f"Baseline mean: {report.baseline_statistics.mean:.6f}",
        f"Candidate: {report.candidate_variant}",
        f"Candidate mean: {report.candidate_statistics.mean:.6f}",
        "",
        f"Paired samples: {report.paired_sample_count}",
        f"Mean difference: {report.mean_difference:.6f}",
        (
            "Confidence interval: "
            f"[{report.confidence_interval_lower:.6f}, "
            f"{report.confidence_interval_upper:.6f}]"
        ),
        f"P-value: {report.p_value:.6f}",
        f"Effect size: {report.effect_size:.6f}",
        f"Statistically significant: {report.statistically_significant}",
        f"Practically significant: {report.practical_significance}",
        f"Winner: {winner}",
        f"Experiment passed: {report.passed}",
    ]

    if report.violations:
        lines.append("")
        lines.append("Violations:")

        lines.extend(
            f"- {violation}"
            for violation in report.violations
        )

    return "\n".join(lines)
