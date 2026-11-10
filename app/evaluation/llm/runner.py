import asyncio
import inspect
import time
from collections.abc import Callable
from typing import Any

from app.evaluation.llm.schemas import (
    EvaluationCase,
    EvaluationStatus,
    LLMEvaluationConfig,
    LLMCaseResult,
    ModelResponse,
)


class CallableLLMAdapter:
    """Adapts a synchronous or asynchronous generation callable."""

    def __init__(self, generator: Callable[..., Any], model_name: str = "custom"):
        self.generator = generator
        self.model_name = model_name

    async def generate(self, prompt: str) -> ModelResponse:
        if inspect.iscoroutinefunction(self.generator):
            raw = await self.generator(prompt)
        else:
            raw = await asyncio.to_thread(self.generator, prompt)

        if isinstance(raw, ModelResponse):
            return raw

        if isinstance(raw, str):
            return ModelResponse(text=raw, model_name=self.model_name)

        if isinstance(raw, dict):
            return ModelResponse(
                text=str(raw.get("text", raw.get("content", ""))),
                model_name=str(raw.get("model_name", self.model_name)),
                prompt_tokens=int(raw.get("prompt_tokens", 0)),
                completion_tokens=int(raw.get("completion_tokens", 0)),
                metadata=raw.get("metadata", {}),
            )

        raise TypeError(
            "Generator must return str, dict, or ModelResponse"
        )


class LLMEvaluationRunner:
    def __init__(
        self,
        adapter: Any,
        evaluator: Any,
        config: LLMEvaluationConfig | None = None,
    ):
        self.adapter = adapter
        self.evaluator = evaluator
        self.config = config or LLMEvaluationConfig()

    async def _run_case(
        self,
        case: EvaluationCase,
        semaphore: asyncio.Semaphore,
    ) -> LLMCaseResult:
        async with semaphore:
            started = time.perf_counter()

            try:
                async def execute():
                    response = await self.adapter.generate(case.prompt)
                    scores = self.evaluator.evaluate(case, response)

                    if inspect.isawaitable(scores):
                        scores = await scores

                    return response, scores

                response, scores = await asyncio.wait_for(
                    execute(),
                    timeout=self.config.timeout_seconds,
                )

                latency_ms = (time.perf_counter() - started) * 1000

                cost = (
                    response.prompt_tokens
                    * self.config.prompt_cost_per_1k_tokens
                    / 1000
                    + response.completion_tokens
                    * self.config.completion_cost_per_1k_tokens
                    / 1000
                )

                average = (
                    sum(item.score for item in scores) / len(scores)
                    if scores else 0.0
                )

                return LLMCaseResult(
                    case_id=case.case_id,
                    status=(
                        EvaluationStatus.PASSED
                        if average >= self.config.pass_threshold
                        else EvaluationStatus.FAILED
                    ),
                    response=response.text,
                    scores=list(scores),
                    latency_ms=latency_ms,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    estimated_cost=cost,
                    metadata={"model_name": response.model_name},
                )

            except Exception as exc:
                latency_ms = (time.perf_counter() - started) * 1000
                return LLMCaseResult(
                    case_id=case.case_id,
                    status=EvaluationStatus.ERROR,
                    latency_ms=latency_ms,
                    error=f"{type(exc).__name__}: {exc}",
                )

    async def run(
        self,
        cases: list[EvaluationCase],
    ) -> list[LLMCaseResult]:
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        tasks = [
            self._run_case(case, semaphore)
            for case in cases
        ]
        return await asyncio.gather(*tasks)
