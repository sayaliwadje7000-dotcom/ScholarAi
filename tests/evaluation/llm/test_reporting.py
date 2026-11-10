import json

from app.evaluation.llm.reporting import (
    compare_experiments,
    export_json_report,
    summarize_results,
)
from app.evaluation.llm.schemas import (
    EvaluationDimension,
    EvaluationStatus,
    LLMCaseResult,
    DimensionScore,
)


def make_result(case_id, score=0.8, status=EvaluationStatus.PASSED):
    return LLMCaseResult(
        case_id=case_id,
        status=status,
        scores=[
            DimensionScore(EvaluationDimension.RELEVANCE, score)
        ],
        latency_ms=100,
        prompt_tokens=100,
        completion_tokens=50,
        estimated_cost=0.01,
    )


def test_summary_counts_results():
    summary = summarize_results([
        make_result("1"),
        make_result("2", status=EvaluationStatus.FAILED),
        make_result("3", status=EvaluationStatus.ERROR),
    ])

    assert summary["total_cases"] == 3
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["errors"] == 1


def test_summary_calculates_pass_rate():
    summary = summarize_results([
        make_result("1"),
        make_result("2", status=EvaluationStatus.FAILED),
    ])

    assert summary["pass_rate"] == 0.5


def test_summary_calculates_average_quality():
    summary = summarize_results([
        make_result("1", 0.6),
        make_result("2", 1.0),
    ])

    assert summary["average_quality_score"] == 0.8


def test_summary_handles_empty_results():
    summary = summarize_results([])
    assert summary["total_cases"] == 0
    assert summary["pass_rate"] == 0.0


def test_experiment_comparison():
    comparison = compare_experiments({
        "baseline": [make_result("1", 0.6)],
        "candidate": [make_result("2", 0.9)],
    })

    assert comparison["candidate"]["average_quality_score"] == 0.9


def test_json_report_is_valid():
    serialized = export_json_report([make_result("1")])
    parsed = json.loads(serialized)

    assert parsed["summary"]["total_cases"] == 1
    assert parsed["results"][0]["case_id"] == "1"


def test_json_report_writes_file(tmp_path):
    destination = tmp_path / "report.json"
    export_json_report([make_result("1")], destination)

    assert destination.exists()
    assert json.loads(destination.read_text())["summary"]["total_cases"] == 1
