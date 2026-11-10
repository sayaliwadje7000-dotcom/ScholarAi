import json

from pathlib import Path
from typing import Any

from app.evaluation.rag.schemas import RAGBenchmarkReport


def export_rag_report(
    report: RAGBenchmarkReport,
    destination: str | Path | None = None,
) -> str:
    if not isinstance(report, RAGBenchmarkReport):
        raise TypeError(
            "report must be a RAGBenchmarkReport"
        )

    serialized = json.dumps(
        report.to_dict(),
        indent=2,
        ensure_ascii=False,
    )

    if destination is not None:
        path = Path(destination)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            serialized,
            encoding="utf-8",
        )

    return serialized


def compare_rag_experiments(
    experiments: dict[str, RAGBenchmarkReport],
) -> dict[str, Any]:
    if not experiments:
        raise ValueError(
            "At least one experiment is required"
        )

    comparison = {}

    for name, report in experiments.items():
        if not isinstance(report, RAGBenchmarkReport):
            raise TypeError(
                f"Experiment {name} is not a RAGBenchmarkReport"
            )

        comparison[name] = {
            "dataset_name": report.dataset_name,
            "total_cases": report.total_cases,
            "passed_cases": report.passed_cases,
            "failed_cases": report.failed_cases,
            "error_cases": report.error_cases,
            "pass_rate": report.pass_rate,
            "average_metrics": report.average_metrics,
        }

    return comparison
