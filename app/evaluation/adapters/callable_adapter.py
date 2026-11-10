"""Explicit adapter for existing synchronous or asynchronous evaluators."""

import asyncio
import inspect

from app.evaluation.core.base import (
    Evaluator,
    EvaluatorType
)


class CallableEvaluatorAdapter(Evaluator):

    def __init__(
        self,
        evaluator_id,
        evaluator_type,
        operation,
        *,
        version="1.0",
        validator=None
    ):

        if not callable(operation):

            raise TypeError(
                "operation must be callable."
            )

        self.evaluator_id = evaluator_id

        self.evaluator_type = EvaluatorType(
            evaluator_type
        )

        self.version = version

        self._operation = operation

        self._validator = validator

    def validate_input(self, payload):

        super().validate_input(payload)

        if self._validator is not None:

            self._validator(payload)

    async def evaluate(
        self,
        payload,
        context
    ):

        # Keep synchronous CPU/blocking work off
        # the orchestrator event loop.

        if inspect.iscoroutinefunction(
            self._operation
        ):

            return await self._operation(
                payload
            )

        result = await asyncio.to_thread(
            self._operation,
            payload
        )

        if inspect.isawaitable(result):

            return await result

        return result