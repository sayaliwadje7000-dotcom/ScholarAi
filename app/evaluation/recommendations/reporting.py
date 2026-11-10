import json
from pathlib import Path


def report_to_dict(report):
    return report.model_dump(mode="json")


def save_report(report, path):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report_to_dict(report), indent=2),
        encoding="utf-8",
    )


def render_report(report):
    lines = [
        f"Recommendation Evaluation: {report.dataset_name}",
        f"Dataset version: {report.dataset_version}",
        f"Total cases: {report.total_cases}",
        f"Passed: {report.passed_cases}",
        f"Failed: {report.failed_cases}",
        f"Pass rate: {report.pass_rate:.2%}",
        "",
        "Average metrics:",
    ]

    for name, value in sorted(report.average_metrics.items()):
        lines.append(f"- {name}: {value:.4f}")

    return "\n".join(lines)
