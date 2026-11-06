import pytest

from app.schemas.rag_evaluation import RAGEvaluationCase

from app.services.rag.evaluation import RAGEvaluator


def create_case(
    answerable=True,
):
    return RAGEvaluationCase(
        case_id="rag-001",
        query="What is machine learning?",
        expected_chunk_ids=["chunk-1", "chunk-2"],
        reference_answer=(
            "Machine learning is a branch of artificial "
            "intelligence that learns from data."
        ),
        required_terms=[
            "machine learning",
            "artificial intelligence",
        ],
        expected_citation_source_ids=["S1"],
        answerable=answerable,
    )


def create_result(
    grounding_status="citation_checks_passed",
    grounded=True,
):
    return {
        "answer": (
            "Machine learning is a branch of artificial "
            "intelligence that learns from data."
        ),
        "retrieved_chunks": [
            {"chunk_id": "chunk-1"},
            {"chunk_id": "chunk-2"},
        ],
        "citations": [
            {"source_id": "S1"},
        ],
        "grounding_status": grounding_status,
        "grounded": grounded,
    }


def test_evaluate_case_passes():
    evaluator = RAGEvaluator()

    result = evaluator.evaluate_case(
        create_case(),
        create_result(),
        latency_ms=100,
    )

    assert result.passed is True
    assert result.failed_checks == []

    assert result.metrics.recall_at_k == 1.0
    assert result.metrics.citation_precision == 1.0
    assert result.metrics.latency_ms == 100


def test_evaluate_case_detects_bad_retrieval():
    evaluator = RAGEvaluator()

    rag_result = create_result()

    rag_result["retrieved_chunks"] = [
        {"chunk_id": "unrelated"}
    ]

    result = evaluator.evaluate_case(
        create_case(),
        rag_result,
    )

    assert result.passed is False
    assert "retrieval_recall" in result.failed_checks


def test_evaluate_case_detects_bad_citations():
    evaluator = RAGEvaluator()

    rag_result = create_result()

    rag_result["citations"] = [
        {"source_id": "incorrect-source"}
    ]

    result = evaluator.evaluate_case(
        create_case(),
        rag_result,
    )

    assert result.passed is False
    assert "citation_precision" in result.failed_checks


def test_evaluate_case_detects_ungrounded_answer():
    evaluator = RAGEvaluator()

    result = evaluator.evaluate_case(
        create_case(),
        create_result(
            grounded=False,
        ),
    )

    assert result.passed is False
    assert "grounding" in result.failed_checks


def test_correct_abstention():
    evaluator = RAGEvaluator()

    result = evaluator.evaluate_case(
        create_case(answerable=False),
        {
            "answer": (
                "I could not find relevant information "
                "in the selected documents."
            ),
            "retrieved_chunks": [],
            "citations": [],
            "grounding_status": "insufficient_evidence",
            "grounded": False,
        },
    )

    assert result.metrics.abstention_correct is True
    assert "abstention" not in result.failed_checks


def test_incorrect_abstention():
    evaluator = RAGEvaluator()

    result = evaluator.evaluate_case(
        create_case(answerable=False),
        create_result(),
    )

    assert result.metrics.abstention_correct is False
    assert "abstention" in result.failed_checks


def test_negative_latency_rejected():
    evaluator = RAGEvaluator()

    with pytest.raises(ValueError):
        evaluator.evaluate_case(
            create_case(),
            create_result(),
            latency_ms=-1,
        )


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError):
        RAGEvaluator(
            minimum_recall=1.5
        )


def test_empty_dataset_rejected():
    evaluator = RAGEvaluator()

    with pytest.raises(ValueError):
        evaluator.evaluate_dataset(
            dataset_name="test",
            cases=[],
            runner=lambda case: {},
        )


def test_dataset_evaluation():
    evaluator = RAGEvaluator()

    cases = [
        create_case(),
        create_case(),
    ]

    report = evaluator.evaluate_dataset(
        dataset_name="ScholarAI-RAG-Test",
        cases=cases,
        runner=lambda case: create_result(),
    )

    assert report.total_cases == 2
    assert report.passed_cases == 2
    assert report.failed_cases == 0
    assert report.pass_rate == 1.0

    assert (
        report.average_metrics["recall_at_k"]
        == 1.0
    )


def test_async_runner_is_rejected():
    evaluator = RAGEvaluator()

    async def runner(case):
        return create_result()

    with pytest.raises(TypeError):
        evaluator.evaluate_dataset(
            dataset_name="async-test",
            cases=[create_case()],
            runner=runner,
        )