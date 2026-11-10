import json
import re
from typing import Any, Protocol

from app.evaluation.llm.schemas import (
    EvaluationCase,
    EvaluationDimension,
    DimensionScore,
    ModelResponse,
)


def _tokens(text: str) -> list[str]:
    return re.findall(r"\b[\w']+\b", text.lower())


def _f1_score(predicted: list[str], expected: list[str]) -> float:
    if not predicted or not expected:
        return 0.0

    predicted_counts = {}
    expected_counts = {}

    for token in predicted:
        predicted_counts[token] = predicted_counts.get(token, 0) + 1

    for token in expected:
        expected_counts[token] = expected_counts.get(token, 0) + 1

    overlap = sum(
        min(count, expected_counts.get(token, 0))
        for token, count in predicted_counts.items()
    )

    precision = overlap / len(predicted)
    recall = overlap / len(expected)

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


class DeterministicResponseEvaluator:
    """Deterministic heuristic evaluator. Scores are proxies, not factual verification."""

    def evaluate(
        self,
        case: EvaluationCase,
        response: ModelResponse,
    ) -> list[DimensionScore]:
        answer = response.text.strip()
        answer_tokens = _tokens(answer)
        reference_tokens = _tokens(case.reference_answer)

        scores = []

        if reference_tokens:
            correctness = _f1_score(answer_tokens, reference_tokens)
            completeness = (
                len(set(reference_tokens) & set(answer_tokens))
                / len(set(reference_tokens))
            )
        else:
            correctness = 0.0
            completeness = 0.0

        scores.append(DimensionScore(
            EvaluationDimension.CORRECTNESS,
            correctness,
            "Lexical token-overlap F1 against the reference answer.",
        ))

        if case.expected_keywords:
            answer_lower = answer.lower()
            matched = sum(
                keyword.lower() in answer_lower
                for keyword in case.expected_keywords
            )
            relevance = matched / len(case.expected_keywords)
        else:
            relevance = 1.0 if answer else 0.0

        scores.append(DimensionScore(
            EvaluationDimension.RELEVANCE,
            relevance,
            "Coverage of expected keywords.",
        ))

        scores.append(DimensionScore(
            EvaluationDimension.COMPLETENESS,
            completeness,
            "Reference vocabulary coverage proxy.",
        ))

        if case.forbidden_keywords:
            answer_lower = answer.lower()
            violations = sum(
                keyword.lower() in answer_lower
                for keyword in case.forbidden_keywords
            )
            instruction_score = max(
                0.0,
                1.0 - violations / len(case.forbidden_keywords),
            )
        else:
            instruction_score = 1.0

        scores.append(DimensionScore(
            EvaluationDimension.INSTRUCTION_FOLLOWING,
            instruction_score,
            "Penalty for forbidden keyword occurrences.",
        ))

        word_count = len(answer_tokens)
        clarity = 1.0 if 10 <= word_count <= 300 else (
            0.5 if word_count > 0 else 0.0
        )

        scores.append(DimensionScore(
            EvaluationDimension.CLARITY,
            clarity,
            "Basic response-length heuristic; not a readability assessment.",
        ))

        if case.expected_citations:
            answer_lower = answer.lower()
            matched = sum(
                citation.lower() in answer_lower
                for citation in case.expected_citations
            )
            citation_score = matched / len(case.expected_citations)
        else:
            citation_score = 1.0

        scores.append(DimensionScore(
            EvaluationDimension.CITATION_SUPPORT,
            citation_score,
            "Checks expected citation-string presence only.",
        ))

        return scores


class JudgeAdapter(Protocol):
    async def evaluate(
        self,
        case: EvaluationCase,
        response: ModelResponse,
    ) -> Any:
        ...


class LLMJudgeEvaluator:
    """Uses an injected judge adapter; does not call an external model itself."""

    def __init__(self, judge: JudgeAdapter):
        self.judge = judge

    async def evaluate(
        self,
        case: EvaluationCase,
        response: ModelResponse,
    ) -> list[DimensionScore]:
        raw_result = await self.judge.evaluate(case, response)

        if isinstance(raw_result, str):
            raw_result = json.loads(raw_result)

        if not isinstance(raw_result, dict):
            raise ValueError("LLM judge must return a JSON object")

        scores = []

        for dimension in EvaluationDimension:
            value = raw_result.get(dimension.value)

            if value is None:
                continue

            if isinstance(value, dict):
                score = value.get("score")
                explanation = value.get("explanation", "")
            else:
                score = value
                explanation = ""

            scores.append(DimensionScore(
                dimension=dimension,
                score=float(score),
                explanation=str(explanation),
            ))

        if not scores:
            raise ValueError("LLM judge returned no recognized evaluation scores")

        return scores
