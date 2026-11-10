"""Coordinates evaluator lookup, validation, lifecycle, timeout and normalization."""

import asyncio
import logging
import math
import time

from datetime import datetime, timezone

from collections.abc import Mapping

from typing import Any

from app.evaluation.core.configuration import (
    EvaluationConfig
)

from app.evaluation.core.context import (
    EvaluationContext
)

from app.evaluation.core.exceptions import (
    EvaluationExecutionError,
    EvaluationTimeoutError,
    InvalidEvaluatorInputError,
)

from app.evaluation.core.lifecycle import (
    EvaluationLifecycle,
    EvaluationStatus,
)

from app.evaluation.core.result import (
    EvaluationResult
)


logger = logging.getLogger(__name__)


def _json_safe_metrics(value: Any) -> dict[str, Any]:

    if hasattr(value, "model_dump"):

        value = value.model_dump(
            mode="json"
        )

    elif (
        hasattr(value, "to_dict")
        and callable(value.to_dict)
    ):

        value = value.to_dict()

    elif hasattr(value, "__dataclass_fields__"):

        from dataclasses import asdict

        value = asdict(value)

    if not isinstance(value, Mapping):

        raise TypeError(
            "Evaluator output must be a mapping, Pydantic model, "
            "dataclass, or expose to_dict()."
        )

    result = dict(value)

    for key, item in result.items():

        if not isinstance(key, str):

            raise TypeError(
                "Metric keys must be strings."
            )

        if (
            isinstance(item, float)
            and not math.isfinite(item)
        ):

            raise ValueError(
                f"Metric '{key}' is not finite."
            )

    return result


class EvaluationOrchestrator:

    def __init__(
        self,
        registry,
        *,
        logger_instance=None
    ) -> None:

        self.registry = registry

        self.logger = (
            logger_instance
            or logger
        )

    async def run(
        self,
        config: EvaluationConfig,
        payload: Any
    ) -> EvaluationResult:

        if not isinstance(
            config,
            EvaluationConfig
        ):

            raise TypeError(
                "config must be an EvaluationConfig."
            )

        evaluator = self.registry.get(
            config.evaluator_id
        )

        context = EvaluationContext.create(
            config
        )

        lifecycle = EvaluationLifecycle()

        started_clock = time.perf_counter()

        lifecycle.transition(
            EvaluationStatus.RUNNING
        )

        try:

            evaluator.validate_input(
                payload
            )

            output = await asyncio.wait_for(

                evaluator.evaluate(
                    payload,
                    context
                ),

                timeout=config.timeout_seconds

            )

            metrics = _json_safe_metrics(
                output
            )

            completed_at = datetime.now(
                timezone.utc
            )

            lifecycle.transition(
                EvaluationStatus.COMPLETED
            )

            return EvaluationResult(

                execution_id=context.execution_id,

                evaluator_id=context.evaluator_id,

                evaluator_type=getattr(
                    getattr(
                        evaluator,
                        "evaluator_type",
                        "custom"
                    ),
                    "value",
                    getattr(
                        evaluator,
                        "evaluator_type",
                        "custom"
                    )
                ),

                evaluator_version=str(
                    getattr(
                        evaluator,
                        "version",
                        "1.0"
                    )
                ),

                status=lifecycle.status.value,

                metrics=metrics,

                started_at=context.started_at,

                completed_at=completed_at,

                duration_ms=max(
                    0.0,
                    (
                        time.perf_counter()
                        - started_clock
                    ) * 1000
                ),

                dataset_name=context.dataset_name,

                dataset_version=context.dataset_version,

                model_name=context.model_name,

                model_version=context.model_version,

                prompt_version=context.prompt_version,

                metadata={
                    "tags": dict(context.tags)
                },
            )

        except asyncio.TimeoutError as exc:

            lifecycle.transition(
                EvaluationStatus.FAILED
            )

            self.logger.warning(
                "Evaluation timed out: evaluator_id=%s execution_id=%s",
                context.evaluator_id,
                context.execution_id
            )

            raise EvaluationTimeoutError(

                f"Evaluation '{context.evaluator_id}' "
                f"exceeded {config.timeout_seconds} seconds."

            ) from exc

        except (
            KeyboardInterrupt,
            SystemExit,
            asyncio.CancelledError
        ):

            if (
                lifecycle.status
                == EvaluationStatus.RUNNING
            ):

                lifecycle.transition(
                    EvaluationStatus.CANCELLED
                )

            raise

        except Exception as exc:

            if (
                lifecycle.status
                == EvaluationStatus.RUNNING
            ):

                lifecycle.transition(
                    EvaluationStatus.FAILED
                )

            self.logger.exception(
                "Evaluation failed: evaluator_id=%s execution_id=%s",
                context.evaluator_id,
                context.execution_id
            )

            if isinstance(
                exc,
                (
                    InvalidEvaluatorInputError,
                    EvaluationExecutionError
                )
            ):

                raise

            raise EvaluationExecutionError(

                f"Evaluation '{context.evaluator_id}' "
                f"failed: {type(exc).__name__}."

            ) from exc

    def run_sync(
        self,
        config: EvaluationConfig,
        payload: Any
    ) -> EvaluationResult:

        try:

            asyncio.get_running_loop()

        except RuntimeError:

            return asyncio.run(
                self.run(
                    config,
                    payload
                )
            )

        raise RuntimeError(
            "run_sync cannot be called from an active event loop; "
            "await run() instead."
        )