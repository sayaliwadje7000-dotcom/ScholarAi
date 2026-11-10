import asyncio
import inspect

from collections.abc import Callable
from typing import Any

from app.schemas.rag_evaluation import RAGEvaluationCase


class CallableRAGAdapter:
    """
    Adapter for an existing ScholarAI RAG pipeline.

    Supports:
    - Synchronous pipeline functions.
    - Asynchronous pipeline functions.
    - Synchronous functions returning awaitables.

    The adapter does not modify the production RAG pipeline.
    """

    def __init__(
        self,
        pipeline: Callable[[RAGEvaluationCase], Any],
    ):
        if not callable(pipeline):
            raise TypeError(
                "pipeline must be callable"
            )

        self.pipeline = pipeline

    async def run(
        self,
        case: RAGEvaluationCase,
    ) -> Any:
        if inspect.iscoroutinefunction(self.pipeline):
            return await self.pipeline(case)

        result = await asyncio.to_thread(
            self.pipeline,
            case,
        )

        if inspect.isawaitable(result):
            return await result

        return result
