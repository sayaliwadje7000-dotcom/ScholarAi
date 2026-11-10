import json
from pathlib import Path

from app.evaluation.finalization.schemas import (
    FinalEvaluationReport,
)


class FinalEvaluationReporter:
    """Serializes final evaluation reports."""

    @staticmethod
    def to_dict(report: FinalEvaluationReport) -> dict:
        return report.model_dump(mode="json")

    @staticmethod
    def to_json(
        report: FinalEvaluationReport,
        indent: int = 2,
    ) -> str:
        return json.dumps(
            FinalEvaluationReporter.to_dict(report),
            indent=indent,
            ensure_ascii=False,
        )

    @staticmethod
    def to_text(report: FinalEvaluationReport) -> str:
        lines = [
            "SCHOLARAI FINAL EVALUATION REPORT",
            "=" * 42,
            f"Report ID: {report.report_id}",
            f"Overall status: {report.status.value.upper()}",
            f"Success rate: {report.success_rate:.2f}%",
            "",
            "SUMMARY",
            "-" * 42,
            report.summary,
            "",
            "EVALUATION RESULTS",
            "-" * 42,
        ]

        for result in report.results:
            lines.extend([
                f"Name: {result.check_name}",
                f"Category: {result.category}",
                f"Status: {result.status.value}",
                f"Message: {result.message}",
                f"Duration: {result.duration_seconds:.6f}s",
                "",
            ])

        lines.extend([
            "TOTALS",
            "-" * 42,
            f"Total: {report.total_checks}",
            f"Passed: {report.passed_checks}",
            f"Failed: {report.failed_checks}",
            f"Partial: {report.partial_checks}",
            f"Not run: {report.not_run_checks}",
        ])

        return "\n".join(lines)

    @staticmethod
    def save_json(
        report: FinalEvaluationReport,
        path: str | Path,
    ) -> Path:
        destination = Path(path)
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination.write_text(
            FinalEvaluationReporter.to_json(report),
            encoding="utf-8",
        )
        return destination

    @staticmethod
    def save_text(
        report: FinalEvaluationReport,
        path: str | Path,
    ) -> Path:
        destination = Path(path)
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination.write_text(
            FinalEvaluationReporter.to_text(report),
            encoding="utf-8",
        )
        return destination
