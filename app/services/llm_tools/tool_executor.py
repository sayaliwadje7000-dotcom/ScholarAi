import asyncio
import json
import logging
import time

from typing import Any

from pydantic import ValidationError

from app.core.llm_tool_config import (
    LLMToolSettings,
    llm_tool_settings,
)

from app.schemas.llm_tools import (
    ToolCallRequest,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolExecutionStatus,
)

from app.services.llm_tools.tool_registry import (
    ToolRegistry,
    tool_registry,
)


logger = logging.getLogger(__name__)


class ToolExecutionService:

    def __init__(
        self,
        registry: ToolRegistry = tool_registry,
        settings: LLMToolSettings = llm_tool_settings,
    ):

        self.registry = registry
        self.settings = settings

    def _result(
        self,
        call: ToolCallRequest,
        status: ToolExecutionStatus,
        started_at: float,
        output: Any = None,
        error: str | None = None,
    ) -> ToolExecutionResult:

        elapsed_ms = (
            time.perf_counter() - started_at
        ) * 1000

        return ToolExecutionResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            status=status,
            output=output,
            error=error,
            execution_time_ms=round(
                elapsed_ms,
                3,
            ),
        )

    def _validate_argument_size(
        self,
        arguments: dict[str, Any],
    ) -> bool:

        try:
            serialized = json.dumps(
                arguments,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        except (
            TypeError,
            ValueError,
        ):
            return False

        return (
            len(serialized.encode("utf-8"))
            <= self.settings.max_tool_arguments_bytes
        )

    async def execute(
        self,
        call: ToolCallRequest,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:

        started_at = time.perf_counter()

        definition = self.registry.get(
            call.tool_name
        )

        if definition is None:

            return self._result(
                call,
                ToolExecutionStatus.TOOL_NOT_FOUND,
                started_at,
                error="Requested tool is not available.",
            )

        if not self._validate_argument_size(
            call.arguments
        ):

            return self._result(
                call,
                ToolExecutionStatus.INVALID_ARGUMENTS,
                started_at,
                error="Tool arguments are invalid or exceed the size limit.",
            )

        try:

            validated_arguments = (
                definition.arguments_model.model_validate(
                    call.arguments
                )
            )

        except ValidationError:

            logger.warning(
                "Tool argument validation failed: "
                "tool=%s request_id=%s",
                call.tool_name,
                context.request_id,
            )

            return self._result(
                call,
                ToolExecutionStatus.INVALID_ARGUMENTS,
                started_at,
                error="Tool arguments failed schema validation.",
            )

        if (
            definition.requires_authenticated_user
            and not context.user_id
        ):

            logger.warning(
                "Tool authorization rejected: "
                "tool=%s request_id=%s",
                call.tool_name,
                context.request_id,
            )

            return self._result(
                call,
                ToolExecutionStatus.UNAUTHORIZED,
                started_at,
                error="This tool requires an authenticated user.",
            )

        try:

            output = await asyncio.wait_for(
                definition.handler(
                    validated_arguments,
                    context,
                ),
                timeout=(
                    self.settings.tool_execution_timeout_seconds
                ),
            )

        except asyncio.TimeoutError:

            logger.warning(
                "Tool execution timed out: "
                "tool=%s request_id=%s",
                call.tool_name,
                context.request_id,
            )

            return self._result(
                call,
                ToolExecutionStatus.TIMEOUT,
                started_at,
                error="Tool execution exceeded its time limit.",
            )

        except Exception:

            logger.exception(
                "Tool execution failed: "
                "tool=%s request_id=%s",
                call.tool_name,
                context.request_id,
            )

            return self._result(
                call,
                ToolExecutionStatus.EXECUTION_FAILED,
                started_at,
                error="Tool execution failed.",
            )

        try:

            serialized_output = json.dumps(
                output,
                ensure_ascii=False,
                allow_nan=False,
            )

        except (
            TypeError,
            ValueError,
        ):

            return self._result(
                call,
                ToolExecutionStatus.EXECUTION_FAILED,
                started_at,
                error="Tool returned an invalid structured result.",
            )

        if (
            len(serialized_output)
            > self.settings.max_tool_output_characters
        ):

            return self._result(
                call,
                ToolExecutionStatus.OUTPUT_TOO_LARGE,
                started_at,
                error="Tool output exceeded the configured size limit.",
            )

        logger.info(
            "Tool execution completed: "
            "tool=%s request_id=%s",
            call.tool_name,
            context.request_id,
        )

        return self._result(
            call,
            ToolExecutionStatus.SUCCESS,
            started_at,
            output=output,
        )

    async def execute_many(
        self,
        calls: list[ToolCallRequest],
        context: ToolExecutionContext,
    ) -> list[ToolExecutionResult]:

        if len(calls) > self.settings.max_tool_calls_per_request:

            return [
                self._result(
                    call,
                    ToolExecutionStatus.INVALID_ARGUMENTS,
                    time.perf_counter(),
                    error="Maximum tool calls per request exceeded.",
                )
                for call in calls
            ]

        results = []

        # Sequential execution preserves ordering and avoids
        # uncontrolled parallel side effects.
        for call in calls:

            result = await self.execute(
                call,
                context,
            )

            results.append(result)

        return results


tool_execution_service = ToolExecutionService()