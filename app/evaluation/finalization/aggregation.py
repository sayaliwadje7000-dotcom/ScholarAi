from app.evaluation.finalization.schemas import (
    EvaluationCheckResult,
    FinalEvaluationStatus,
)


def aggregate_evaluation_results(
    results: list[EvaluationCheckResult],
) -> dict[str, object]:
    total = len(results)

    passed = sum(
        result.status == FinalEvaluationStatus.PASSED
        for result in results
    )

    failed = sum(
        result.status == FinalEvaluationStatus.FAILED
        for result in results
    )

    partial = sum(
        result.status == FinalEvaluationStatus.PARTIAL
        for result in results
    )

    not_run = sum(
        result.status == FinalEvaluationStatus.NOT_RUN
        for result in results
    )

    success_rate = (
        (passed / total) * 100.0
        if total
        else 0.0
    )

    if total == 0:
        overall_status = FinalEvaluationStatus.NOT_RUN
    elif failed == total:
        overall_status = FinalEvaluationStatus.FAILED
    elif failed > 0:
        overall_status = FinalEvaluationStatus.FAILED
    elif partial > 0 or not_run > 0:
        overall_status = FinalEvaluationStatus.PARTIAL
    else:
        overall_status = FinalEvaluationStatus.PASSED

    return {
        "status": overall_status,
        "total_checks": total,
        "passed_checks": passed,
        "failed_checks": failed,
        "partial_checks": partial,
        "not_run_checks": not_run,
        "success_rate": round(success_rate, 2),
    }
