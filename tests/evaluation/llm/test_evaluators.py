import pytest

from app.evaluation.llm.evaluators import (
    DeterministicResponseEvaluator,
    LLMJudgeEvaluator,
)
from app.evaluation.llm.schemas import (
    EvaluationCase,
    EvaluationDimension,
    ModelResponse,
)


def test_deterministic_evaluator_returns_all_dimensions():
    evaluator = DeterministicResponseEvaluator()
    case = EvaluationCase("1", "Explain", reference_answer="retrieval augmented generation")
    response = ModelResponse("retrieval augmented generation is useful")
    scores = evaluator.evaluate(case, response)

    assert len(scores) == len(EvaluationDimension)


def test_deterministic_evaluator_scores_expected_keywords():
    evaluator = DeterministicResponseEvaluator()
    case = EvaluationCase(
        "1",
        "Explain RAG",
        expected_keywords=("retrieval", "generation"),
    )
    response = ModelResponse("Retrieval and generation are used.")
    scores = evaluator.evaluate(case, response)

    relevance = next(
        item for item in scores
        if item.dimension == EvaluationDimension.RELEVANCE
    )
    assert relevance.score == 1.0


def test_deterministic_evaluator_penalizes_forbidden_keywords():
    evaluator = DeterministicResponseEvaluator()
    case = EvaluationCase(
        "1",
        "Answer",
        forbidden_keywords=("guaranteed",),
    )
    response = ModelResponse("This is guaranteed to work.")
    scores = evaluator.evaluate(case, response)

    instruction = next(
        item for item in scores
        if item.dimension == EvaluationDimension.INSTRUCTION_FOLLOWING
    )
    assert instruction.score == 0.0


def test_judge_evaluator_accepts_valid_scores():
    class FakeJudge:
        async def evaluate(self, case, response):
            return {"correctness": {"score": 0.9, "explanation": "Good"}}

    evaluator = LLMJudgeEvaluator(FakeJudge())
    case = EvaluationCase("1", "Question")
    response = ModelResponse("Answer")

    scores = __import__("asyncio").run(
        evaluator.evaluate(case, response)
    )
    assert scores[0].score == 0.9


def test_judge_evaluator_rejects_empty_scores():
    class FakeJudge:
        async def evaluate(self, case, response):
            return {}

    evaluator = LLMJudgeEvaluator(FakeJudge())
    case = EvaluationCase("1", "Question")
    response = ModelResponse("Answer")

    with pytest.raises(ValueError):
        __import__("asyncio").run(
            evaluator.evaluate(case, response)
        )
