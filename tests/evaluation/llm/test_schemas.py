import pytest

from app.evaluation.llm.schemas import (
    EvaluationCase,
    EvaluationDimension,
    EvaluationStatus,
    LLMEvaluationConfig,
    LLMCaseResult,
    ModelResponse,
    DimensionScore,
)


def test_evaluation_case_creation():
    case = EvaluationCase("case-1", "Explain RAG")
    assert case.case_id == "case-1"


def test_evaluation_case_rejects_empty_id():
    with pytest.raises(ValueError):
        EvaluationCase("", "Explain RAG")


def test_evaluation_case_rejects_empty_prompt():
    with pytest.raises(ValueError):
        EvaluationCase("case-1", " ")


def test_model_response_rejects_negative_tokens():
    with pytest.raises(ValueError):
        ModelResponse("answer", prompt_tokens=-1)


def test_dimension_score_rejects_out_of_range():
    with pytest.raises(ValueError):
        DimensionScore(EvaluationDimension.CLARITY, 1.5)


def test_config_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        LLMEvaluationConfig(pass_threshold=2.0)


def test_config_rejects_zero_timeout():
    with pytest.raises(ValueError):
        LLMEvaluationConfig(timeout_seconds=0)


def test_config_rejects_zero_concurrency():
    with pytest.raises(ValueError):
        LLMEvaluationConfig(max_concurrency=0)


def test_result_average_quality_score():
    result = LLMCaseResult(
        case_id="case-1",
        status=EvaluationStatus.PASSED,
        scores=[
            DimensionScore(EvaluationDimension.CLARITY, 0.8),
            DimensionScore(EvaluationDimension.RELEVANCE, 1.0),
        ],
    )
    assert result.average_quality_score == pytest.approx(0.9)
