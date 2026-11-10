import asyncio

from app.evaluation.llm.evaluators import DeterministicResponseEvaluator
from app.evaluation.llm.runner import CallableLLMAdapter, LLMEvaluationRunner
from app.evaluation.llm.schemas import (
    EvaluationCase,
    EvaluationStatus,
    LLMEvaluationConfig,
    ModelResponse,
)


def test_runner_evaluates_cases():
    adapter = CallableLLMAdapter(lambda prompt: "A useful answer")
    runner = LLMEvaluationRunner(adapter, DeterministicResponseEvaluator())

    results = asyncio.run(
        runner.run([
            EvaluationCase(
                "1",
                "Explain something",
                reference_answer="A useful answer",
            )
        ])
    )

    assert len(results) == 1
    assert results[0].status == EvaluationStatus.PASSED
    assert results[0].average_quality_score >= 0.7


def test_runner_handles_multiple_cases():
    adapter = CallableLLMAdapter(lambda prompt: "A useful answer")
    runner = LLMEvaluationRunner(adapter, DeterministicResponseEvaluator())

    cases = [
        EvaluationCase("1", "Question one", reference_answer="A useful answer"),
        EvaluationCase("2", "Question two", reference_answer="A useful answer"),
    ]

    results = asyncio.run(runner.run(cases))
    assert len(results) == 2


def test_runner_records_generation_errors():
    def failing_generator(prompt):
        raise RuntimeError("generation failed")

    adapter = CallableLLMAdapter(failing_generator)
    runner = LLMEvaluationRunner(adapter, DeterministicResponseEvaluator())

    results = asyncio.run(
        runner.run([EvaluationCase("1", "Question")])
    )

    assert results[0].status == EvaluationStatus.ERROR
    assert "generation failed" in results[0].error


def test_runner_records_token_cost():
    adapter = CallableLLMAdapter(
        lambda prompt: ModelResponse(
            text="A useful answer",
            prompt_tokens=1000,
            completion_tokens=500,
        )
    )
    config = LLMEvaluationConfig(
        prompt_cost_per_1k_tokens=0.01,
        completion_cost_per_1k_tokens=0.02,
    )
    runner = LLMEvaluationRunner(
        adapter,
        DeterministicResponseEvaluator(),
        config,
    )

    results = asyncio.run(
        runner.run([
            EvaluationCase(
                "1",
                "Question",
                reference_answer="A useful answer",
            )
        ])
    )

    assert results[0].estimated_cost == 0.02


def test_runner_handles_timeout():
    async def slow_generator(prompt):
        await asyncio.sleep(0.1)
        return "Answer"

    adapter = CallableLLMAdapter(slow_generator)
    config = LLMEvaluationConfig(timeout_seconds=0.01)
    runner = LLMEvaluationRunner(
        adapter,
        DeterministicResponseEvaluator(),
        config,
    )

    results = asyncio.run(
        runner.run([EvaluationCase("1", "Question")])
    )

    assert results[0].status == EvaluationStatus.ERROR
    assert "TimeoutError" in results[0].error
