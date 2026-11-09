import logging
import time
import uuid

from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.schemas.ai_workflows import (
    WorkflowExecutionResult,
    WorkflowFailurePolicy,
    WorkflowStatus,
    WorkflowStepResult,
    WorkflowStepStatus,
)
from app.schemas.llm_tools import (
    ToolCallRequest,
    ToolExecutionContext,
    ToolExecutionStatus,
)

from app.services.ai_workflows.exceptions import (
    WorkflowInputValidationError,
    WorkflowNotFoundError,
    WorkflowReferenceResolutionError,
)

from app.services.ai_workflows.workflow_registry import (
    WorkflowDefinition,
    WorkflowRegistry,
    workflow_registry,
)

from app.services.ai_workflows.workflow_resolver import (
    WorkflowReferenceResolver,
    workflow_reference_resolver,
)

from app.services.ai_workflows.workflow_state import (
    WorkflowStateMachine,
)

from app.services.llm_tools.tool_executor import (
    ToolExecutionService,
    tool_execution_service,
)


logger = logging.getLogger(__name__)


class WorkflowExecutionEngine:

    def __init__(
        self,
        registry: WorkflowRegistry = workflow_registry,
        tool_executor: ToolExecutionService = (
            tool_execution_service
        ),
        resolver: WorkflowReferenceResolver = (
            workflow_reference_resolver
        ),
    ):

        self.registry = registry
        self.tool_executor = tool_executor
        self.resolver = resolver

        # In-memory execution tracking.
        # This is not durable across application restarts.
        self._executions: dict[
            str,
            WorkflowExecutionResult
        ] = {}

    @staticmethod
    def _timestamp() -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()

    @staticmethod
    def _topological_order(
        definition: WorkflowDefinition,
    ) -> list:

        steps = {
            step.step_id: step
            for step in definition.steps
        }

        resolved = set()
        ordered = []

        while len(ordered) < len(steps):

            ready = [
                step
                for step in definition.steps
                if step.step_id not in resolved
                and set(step.depends_on).issubset(
                    resolved
                )
            ]

            if not ready:

                raise ValueError(
                    "Workflow dependency graph cannot be resolved."
                )

            for step in ready:

                ordered.append(step)

                resolved.add(step.step_id)

        return ordered

    def get_execution(
        self,
        execution_id: str,
    ) -> WorkflowExecutionResult | None:

        return self._executions.get(
            execution_id
        )

    def list_executions(self) -> list[WorkflowExecutionResult]:

        return list(
            self._executions.values()
        )

    async def execute(
        self,
        workflow_name: str,
        inputs: dict[str, Any],
        context: ToolExecutionContext,
    ) -> WorkflowExecutionResult:

        definition = self.registry.get(
            workflow_name
        )

        if definition is None:

            raise WorkflowNotFoundError(
                f"Workflow '{workflow_name}' is not registered."
            )

        try:

            validated_inputs = (
                definition.input_model.model_validate(
                    inputs
                )
            )

        except ValidationError as exc:

            raise WorkflowInputValidationError(
                "Workflow inputs failed validation."
            ) from exc

        normalized_inputs = (
            validated_inputs.model_dump(mode="json")
        )

        execution_id = str(uuid.uuid4())

        started_at = time.perf_counter()

        started_timestamp = self._timestamp()

        workflow_status = WorkflowStatus.PENDING

        workflow_status = (
            WorkflowStateMachine.transition_workflow(
                workflow_status,
                WorkflowStatus.RUNNING,
            )
        )

        step_results: list[WorkflowStepResult] = []

        step_outputs: dict[
            str,
            dict[str, Any]
        ] = {}

        failed_steps = set()

        successful_steps = set()

        workflow_error = None

        ordered_steps = self._topological_order(
            definition
        )

        for step in ordered_steps:

            step_status = WorkflowStepStatus.PENDING

            # A step cannot run until all dependencies
            # have succeeded.
            if not set(step.depends_on).issubset(
                successful_steps
            ):

                step_status = (
                    WorkflowStateMachine.transition_step(
                        step_status,
                        WorkflowStepStatus.SKIPPED,
                    )
                )

                step_results.append(
                    WorkflowStepResult(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status=step_status,
                        error=(
                            "One or more dependencies "
                            "did not succeed."
                        ),
                        execution_time_ms=0,
                    )
                )

                continue

            step_started = time.perf_counter()

            step_status = (
                WorkflowStateMachine.transition_step(
                    step_status,
                    WorkflowStepStatus.RUNNING,
                )
            )

            try:

                resolved_arguments = (
                    self.resolver.resolve_template(
                        step.arguments_template,
                        normalized_inputs,
                        step_outputs,
                    )
                )

                if not isinstance(
                    resolved_arguments,
                    dict,
                ):

                    raise WorkflowReferenceResolutionError(
                        "Resolved tool arguments must be a dictionary."
                    )

                tool_call = ToolCallRequest(
                    call_id=str(uuid.uuid4()),
                    tool_name=step.tool_name,
                    arguments=resolved_arguments,
                )

                tool_result = await self.tool_executor.execute(
                    tool_call,
                    context,
                )

                if tool_result.status != ToolExecutionStatus.SUCCESS:

                    step_status = (
                        WorkflowStateMachine.transition_step(
                            step_status,
                            WorkflowStepStatus.FAILED,
                        )
                    )

                    failed_steps.add(
                        step.step_id
                    )

                    step_results.append(
                        WorkflowStepResult(
                            step_id=step.step_id,
                            tool_name=step.tool_name,
                            status=step_status,
                            error=(
                                tool_result.error
                                or "Tool execution failed."
                            ),
                            execution_time_ms=(
                                tool_result.execution_time_ms
                            ),
                        )
                    )

                    if (
                        definition.failure_policy
                        == WorkflowFailurePolicy.STOP
                    ):

                        workflow_error = (
                            f"Workflow stopped because "
                            f"step '{step.step_id}' failed."
                        )

                        break

                    continue

                validated_output = (
                    step.output_model.model_validate(
                        tool_result.output
                    )
                )

                output_data = (
                    validated_output.model_dump(
                        mode="json"
                    )
                )

                step_outputs[step.step_id] = output_data

                step_status = (
                    WorkflowStateMachine.transition_step(
                        step_status,
                        WorkflowStepStatus.SUCCEEDED,
                    )
                )

                successful_steps.add(
                    step.step_id
                )

                step_results.append(
                    WorkflowStepResult(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status=step_status,
                        output=output_data,
                        execution_time_ms=(
                            tool_result.execution_time_ms
                        ),
                    )
                )

            except (
                WorkflowReferenceResolutionError,
                ValidationError,
            ):

                step_status = (
                    WorkflowStateMachine.transition_step(
                        step_status,
                        WorkflowStepStatus.FAILED,
                    )
                )

                failed_steps.add(
                    step.step_id
                )

                logger.exception(
                    "Workflow step validation failed: "
                    "workflow=%s step=%s execution_id=%s",
                    workflow_name,
                    step.step_id,
                    execution_id,
                )

                step_results.append(
                    WorkflowStepResult(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status=step_status,
                        error=(
                            "Workflow step input or output "
                            "validation failed."
                        ),
                        execution_time_ms=(
                            (time.perf_counter() - step_started)
                            * 1000
                        ),
                    )
                )

                if (
                    definition.failure_policy
                    == WorkflowFailurePolicy.STOP
                ):

                    workflow_error = (
                        f"Workflow stopped because "
                        f"step '{step.step_id}' failed validation."
                    )

                    break

            if (
                step_status == WorkflowStepStatus.FAILED
                and definition.failure_policy
                == WorkflowFailurePolicy.STOP
            ):

                break

        skipped_steps = {
            result.step_id
            for result in step_results
            if result.status == WorkflowStepStatus.SKIPPED
        }

        not_started_steps = {
            step.step_id
            for step in ordered_steps
        } - {
            result.step_id
            for result in step_results
        }

        # Steps after an early STOP failure were never started.
        for step in ordered_steps:

            if step.step_id in not_started_steps:

                step_results.append(
                    WorkflowStepResult(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status=WorkflowStepStatus.SKIPPED,
                        error="Workflow stopped before this step started.",
                        execution_time_ms=0,
                    )
                )

        if failed_steps:

            if successful_steps:

                workflow_status = (
                    WorkflowStateMachine.transition_workflow(
                        workflow_status,
                        WorkflowStatus.PARTIALLY_SUCCEEDED,
                    )
                )

            else:

                workflow_status = (
                    WorkflowStateMachine.transition_workflow(
                        workflow_status,
                        WorkflowStatus.FAILED,
                    )
                )

        elif skipped_steps or not_started_steps:

            workflow_status = (
                WorkflowStateMachine.transition_workflow(
                    workflow_status,
                    WorkflowStatus.PARTIALLY_SUCCEEDED,
                )
            )

        else:

            workflow_status = (
                WorkflowStateMachine.transition_workflow(
                    workflow_status,
                    WorkflowStatus.SUCCEEDED,
                )
            )

        final_output = None

        if (
            definition.final_output_step
            and definition.final_output_step in step_outputs
        ):

            final_output = step_outputs[
                definition.final_output_step
            ]

        elif workflow_status == WorkflowStatus.SUCCEEDED:

            final_output = (
                step_outputs[
                    ordered_steps[-1].step_id
                ]
            )

        completed_timestamp = self._timestamp()

        execution_time_ms = (
            time.perf_counter() - started_at
        ) * 1000

        result = WorkflowExecutionResult(
            execution_id=execution_id,
            workflow_name=workflow_name,
            status=workflow_status,
            steps=step_results,
            final_output=final_output,
            error=workflow_error,
            started_at=started_timestamp,
            completed_at=completed_timestamp,
            execution_time_ms=round(
                execution_time_ms,
                3,
            ),
        )

        self._executions[execution_id] = result

        logger.info(
            "Workflow execution completed: "
            "workflow=%s execution_id=%s status=%s",
            workflow_name,
            execution_id,
            workflow_status.value,
        )

        return result


workflow_execution_engine = WorkflowExecutionEngine()