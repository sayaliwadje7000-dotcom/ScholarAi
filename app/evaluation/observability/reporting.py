import json
from pathlib import Path
from typing import Any

from app.evaluation.observability.schemas import (
    PerformanceEvaluationReport,
)


def report_to_dict(
    report: PerformanceEvaluationReport,
) -> dict[str, Any]:
    return report.model_dump(mode="json")


def save_report(
    report: PerformanceEvaluationReport,
    path: str | Path,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    destination.write_text(
        json.dumps(report_to_dict(report), indent=2),
        encoding="utf-8",
    )

    return destination


def render_report(
    report: PerformanceEvaluationReport,
) -> str:
    status = "PASSED" if report.passed else "FAILED"

    lines = [
        "SCHOLARAI PERFORMANCE EVALUATION",
        "=" * 42,
        f"Status: {status}",
        "",
        f"Total requests: {report.total_requests}",
        f"Successful requests: {report.successful_requests}",
        f"Failed requests: {report.failed_requests}",
        f"Error rate: {report.error_rate:.4f}",
        "",
        "LATENCY",
        f"Average: {report.average_latency_ms:.2f} ms",
        f"P50: {report.p50_latency_ms:.2f} ms",
        f"P95: {report.p95_latency_ms:.2f} ms",
        f"P99: {report.p99_latency_ms:.2f} ms",
        f"Maximum: {report.maximum_latency_ms:.2f} ms",
        "",
        "THROUGHPUT",
        (
            "Requests/second: "
            f"{report.throughput_requests_per_second:.4f}"
        ),
        "",
        "TOKEN USAGE",
        f"Input tokens: {report.total_input_tokens}",
        f"Output tokens: {report.total_output_tokens}",
        "",
        "COST",
        f"Total estimated cost: ${report.total_estimated_cost_usd:.8f}",
        (
            "Average cost/request: "
            f"${report.average_cost_per_request_usd:.8f}"
        ),
        "",
        "VIOLATIONS",
    ]

    if report.violations:
        lines.extend(f"- {item}" for item in report.violations)
    else:
        lines.append("None")

    return "\n".join(lines)
