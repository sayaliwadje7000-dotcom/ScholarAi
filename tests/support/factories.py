"""Reusable factories for evaluation-related test data."""

from typing import Any
from uuid import uuid4

from app.evaluation.finalization.schemas import (
    EvaluationCheckResult,
    FinalEvaluationReport,
    FinalEvaluationStatus,
)


class EvaluationResultFactory:
    """Build valid evaluation check results for tests."""

    @staticmethod
    def create(**overrides: Any) -> EvaluationCheckResult:
        values = {
            "check_name": "sample_evaluation",
            "category": "unit",
            "status": FinalEvaluationStatus.PASSED,
            "message": "Evaluation completed successfully.",
            "duration_seconds": 0.1,
            "metrics": {},
            "details": {},
        }

        values.update(overrides)

        return EvaluationCheckResult.model_validate(values)

    @staticmethod
    def passed(**overrides: Any) -> EvaluationCheckResult:
        values = {"status": FinalEvaluationStatus.PASSED}
        values.update(overrides)
        return EvaluationResultFactory.create(**values)

    @staticmethod
    def failed(**overrides: Any) -> EvaluationCheckResult:
        values = {"status": FinalEvaluationStatus.FAILED}
        values.update(overrides)
        return EvaluationResultFactory.create(**values)

    @staticmethod
    def partial(**overrides: Any) -> EvaluationCheckResult:
        values = {"status": FinalEvaluationStatus.PARTIAL}
        values.update(overrides)
        return EvaluationResultFactory.create(**values)


class EvaluationReportFactory:
    """Build valid final evaluation reports for tests."""

    @staticmethod
    def create(**overrides: Any) -> FinalEvaluationReport:
        values = dict(overrides)

        results = values.get("results", [])
        results = list(results)

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

        total = len(results)

        calculated_values = {
            "report_id": str(uuid4()),
            "status": (
                FinalEvaluationStatus.PASSED
                if total > 0 and failed == 0 and partial == 0 and not_run == 0
                else FinalEvaluationStatus.NOT_RUN
                if total == 0
                else FinalEvaluationStatus.FAILED
                if failed > 0
                else FinalEvaluationStatus.PARTIAL
            ),
            "total_checks": total,
            "passed_checks": passed,
            "failed_checks": failed,
            "partial_checks": partial,
            "not_run_checks": not_run,
            "success_rate": round(
                (passed / total) * 100, 2
            ) if total else 0.0,
            "results": results,
        }

        calculated_values.update(values)

        return FinalEvaluationReport.model_validate(calculated_values)

    @staticmethod
    def successful(**overrides: Any) -> FinalEvaluationReport:
        values = dict(overrides)
        count = values.pop("count", 1)

        if "results" not in values:
            values["results"] = [
                EvaluationResultFactory.passed(
                    check_name=(
                        "sample_evaluation"
                        if index == 0
                        else f"sample_evaluation_{index + 1}"
                    )
                )
                for index in range(count)
            ]

        values.setdefault("status", FinalEvaluationStatus.PASSED)

        return EvaluationReportFactory.create(**values)
