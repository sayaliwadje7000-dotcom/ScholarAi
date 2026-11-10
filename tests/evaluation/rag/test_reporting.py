import json

import pytest

from app.evaluation.rag.reporting import (
    compare_rag_experiments,
    export_rag_report,
)
from app.evaluation.rag.schemas import (
    RAGBenchmarkCaseOutcome,
    RAGBenchmarkReport,
)


def create_report(
    dataset_name="baseline",
    pass_rate=0.8,
):
    return RAGBenchmarkReport(
        dataset_name=dataset_name,
        total_cases=10,
        passed_cases=8,
        failed_cases=2,
        error_cases=0,
        pass_rate=pass_rate,
        average_metrics={
            "recall_at_k": 0.9,
            "ndcg_at_k": 0.85,
            "hit_rate_at_k": 0.95,
        },
        outcomes=[
            RAGBenchmarkCaseOutcome(
                case_id="case-1",
                retrieval_metrics={
                    "ndcg_at_k": 0.85,
                    "hit_rate_at_k": 1.0,
                },
            )
        ],
    )


def test_export_report_returns_valid_json():
    report = create_report()

    serialized = export_rag_report(report)
    parsed = json.loads(serialized)

    assert parsed["dataset_name"] == "baseline"
    assert parsed["total_cases"] == 10


def test_export_report_writes_file(tmp_path):
    report = create_report()
    destination = tmp_path / "reports" / "rag.json"

    export_rag_report(report, destination)

    assert destination.exists()

    parsed = json.loads(
        destination.read_text(encoding="utf-8")
    )

    assert parsed["pass_rate"] == 0.8


def test_experiment_comparison():
    comparison = compare_rag_experiments({
        "baseline": create_report("baseline", 0.8),
        "candidate": create_report("candidate", 0.9),
    })

    assert comparison["baseline"]["pass_rate"] == 0.8
    assert comparison["candidate"]["pass_rate"] == 0.9


def test_comparison_rejects_empty_experiments():
    with pytest.raises(ValueError):
        compare_rag_experiments({})


def test_export_rejects_invalid_report():
    with pytest.raises(TypeError):
        export_rag_report({})
