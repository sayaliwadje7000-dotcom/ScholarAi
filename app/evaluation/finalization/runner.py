import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.evaluation.finalization.aggregation import (
    aggregate_evaluation_results,
)
from app.evaluation.finalization.exceptions import (
    EvaluationExecutionError,
)
from app.evaluation.finalization.registry import (
    FinalEvaluationRegistry,
)
from app.evaluation.finalization.schemas import (
    EvaluationCheckResult,
    FinalEvaluationReport,
    FinalEvaluationStatus,
)


class FinalEvaluationRunner:
    """Executes registered evaluations and generates a consolidated report."""

    def __init__(
        self,
        registry: FinalEvaluationRegistry,
    ) -> None:
        self.registry = registry

    @staticmethod
    def _normalize_status(value: Any) -> FinalEvaluationStatus:
        try:
            return FinalEvaluationStatus(value)
        except (ValueError, TypeError):
            raise EvaluationExecutionError(
                f"Unsupported evaluator status: {value!r}"
            )

    def _execute_one(
        self,
        name: str,
        category: str,
        evaluator: Any,
    ) -> EvaluationCheckResult:
        started_at = datetime.now(timezone.utc)
        start_time = time.perf_counter()

        try:
            output = evaluator()

            if not isinstance(output, dict):
                raise EvaluationExecutionError(
                    "Evaluator must return a dictionary."
                )

            if "status" not in output:
                raise EvaluationExecutionError(
                    "Evaluator output must contain a status field."
                )

            status = self._normalize_status(output["status"])

            metrics = output.get("metrics", {})
            details = output.get("details", {})

            if not isinstance(metrics, dict):
                raise EvaluationExecutionError(
                    "Evaluator metrics must be a dictionary."
                )

            if not isinstance(details, dict):
                raise EvaluationExecutionError(
                    "Evaluator details must be a dictionary."
                )

            return EvaluationCheckResult(
                check_name=name,
                category=category,
                status=status,
                message=str(output.get("message", "")),
                duration_seconds=max(
                    0.0,
                    time.perf_counter() - start_time,
                ),
                metrics=metrics,
                details=details,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

        except Exception as exc:
            return EvaluationCheckResult(
                check_name=name,
                category=category,
                status=FinalEvaluationStatus.FAILED,
                message=f"{type(exc).__name__}: {exc}",
                duration_seconds=max(
                    0.0,
                    time.perf_counter() - start_time,
                ),
                details={"error_type": type(exc).__name__},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

    def run(
        self,
        selected_evaluations: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FinalEvaluationReport:
        try:
            definitions = self.registry.list_evaluations()

            if selected_evaluations is not None:
                unknown = (
                    set(selected_evaluations)
                    - {item["name"] for item in definitions}
                )

                if unknown:
                    raise EvaluationExecutionError(
                        "Unknown evaluations: "
                        + ", ".join(sorted(unknown))
                    )

                selected = set(selected_evaluations)
                definitions = [
                    item
                    for item in definitions
                    if item["name"] in selected
                ]

            results: list[EvaluationCheckResult] = []

            for definition in definitions:
                registered = self.registry.get(definition["name"])

                result = self._execute_one(
                    name=definition["name"],
                    category=definition["category"],
                    evaluator=registered["evaluator"],
                )

                results.append(result)

            aggregate = aggregate_evaluation_results(results)

            summary = (
                f"Executed {aggregate['total_checks']} evaluations: "
                f"{aggregate['passed_checks']} passed, "
                f"{aggregate['failed_checks']} failed, "
                f"{aggregate['partial_checks']} partial, "
                f"{aggregate['not_run_checks']} not run."
            )

            return FinalEvaluationReport(
                report_id=str(uuid.uuid4()),
                status=aggregate["status"],
                total_checks=aggregate["total_checks"],
                passed_checks=aggregate["passed_checks"],
                failed_checks=aggregate["failed_checks"],
                partial_checks=aggregate["partial_checks"],
                not_run_checks=aggregate["not_run_checks"],
                success_rate=aggregate["success_rate"],
                results=results,
                summary=summary,
                metadata=metadata or {},
            )

        except EvaluationExecutionError:
            raise
        except Exception as exc:
            raise EvaluationExecutionError(
                f"Final evaluation could not be completed: {exc}"
            ) from exc
