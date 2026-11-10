import json
from pathlib import Path
from statistics import mean
from typing import Any

from app.evaluation.llm.schemas import (
    EvaluationStatus,
    LLMCaseResult,
)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def summarize_results(results: list[LLMCaseResult]) -> dict[str, Any]:
    total = len(results)

    passed = sum(
        result.status == EvaluationStatus.PASSED
        for result in results
    )
    failed = sum(
        result.status == EvaluationStatus.FAILED
        for result in results
    )
    errors = sum(
        result.status == EvaluationStatus.ERROR
        for result in results
    )

    valid = [
        result for result in results
        if result.status != EvaluationStatus.ERROR
    ]

    latencies = [result.latency_ms for result in results]

    dimension_scores: dict[str, list[float]] = {}

    for result in valid:
        for score in result.scores:
            dimension_scores.setdefault(
                score.dimension.value, []
            ).append(score.score)

    return {
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": passed / total if total else 0.0,
        "average_quality_score": (
            mean([item.average_quality_score for item in valid])
            if valid else 0.0
        ),
        "average_latency_ms": mean(latencies) if latencies else 0.0,
        "p95_latency_ms": _percentile(latencies, 0.95),
        "total_prompt_tokens": sum(
            result.prompt_tokens for result in results
        ),
        "total_completion_tokens": sum(
            result.completion_tokens for result in results
        ),
        "total_estimated_cost": sum(
            result.estimated_cost for result in results
        ),
        "dimension_scores": {
            name: mean(values)
            for name, values in dimension_scores.items()
        },
    }


def compare_experiments(
    experiments: dict[str, list[LLMCaseResult]],
) -> dict[str, Any]:
    return {
        name: summarize_results(results)
        for name, results in experiments.items()
    }


def export_json_report(
    results: list[LLMCaseResult],
    destination: str | Path | None = None,
) -> str:
    report = {
        "summary": summarize_results(results),
        "results": [
            {
                "case_id": result.case_id,
                "status": result.status.value,
                "response": result.response,
                "scores": [
                    {
                        "dimension": score.dimension.value,
                        "score": score.score,
                        "explanation": score.explanation,
                    }
                    for score in result.scores
                ],
                "latency_ms": result.latency_ms,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "estimated_cost": result.estimated_cost,
                "error": result.error,
                "metadata": result.metadata,
            }
            for result in results
        ],
    }

    serialized = json.dumps(report, indent=2, ensure_ascii=False)

    if destination is not None:
        Path(destination).write_text(serialized, encoding="utf-8")

    return serialized
