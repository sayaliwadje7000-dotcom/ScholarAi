import asyncio

from app.evaluation.rag.adapters import CallableRAGAdapter
from app.evaluation.rag.runner import RAGBenchmarkRunner
from app.evaluation.rag.schemas import RAGBenchmarkConfig

from app.schemas.rag_evaluation import (
    RAGEvaluationCase,
    RAGEvaluationDataset,
)


def create_case():
    return RAGEvaluationCase(
        case_id="case-1",
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
        answerable=True,
    )


def create_result():
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
        "grounding_status": "citation_checks_passed",
        "grounded": True,
    }


def create_dataset():
    return RAGEvaluationDataset(
        dataset_name="ScholarAI-RAG-Test",
        cases=[create_case()],
    )


def test_runner_evaluates_rag_dataset():
    adapter = CallableRAGAdapter(
        lambda case: create_result()
    )

    runner = RAGBenchmarkRunner(adapter)

    report = asyncio.run(
        runner.run(create_dataset())
    )

    assert report.total_cases == 1
    assert report.passed_cases == 1
    assert report.failed_cases == 0
    assert report.error_cases == 0
    assert report.pass_rate == 1.0


def test_runner_calculates_ndcg_and_hit_rate():
    adapter = CallableRAGAdapter(
        lambda case: create_result()
    )

    runner = RAGBenchmarkRunner(adapter)

    report = asyncio.run(
        runner.run(create_dataset())
    )

    metrics = report.average_metrics

    assert metrics["ndcg_at_k"] == 1.0
    assert metrics["hit_rate_at_k"] == 1.0


def test_runner_records_pipeline_errors():
    def failing_pipeline(case):
        raise RuntimeError("Pipeline failed")

    runner = RAGBenchmarkRunner(
        CallableRAGAdapter(failing_pipeline)
    )

    report = asyncio.run(
        runner.run(create_dataset())
    )

    assert report.error_cases == 1
    assert report.passed_cases == 0
    assert report.outcomes[0].status == "error"
    assert "Pipeline failed" in report.outcomes[0].error


def test_runner_handles_timeout():
    async def slow_pipeline(case):
        await asyncio.sleep(0.1)
        return create_result()

    config = RAGBenchmarkConfig(
        timeout_seconds=0.01
    )

    runner = RAGBenchmarkRunner(
        CallableRAGAdapter(slow_pipeline),
        config,
    )

    report = asyncio.run(
        runner.run(create_dataset())
    )

    assert report.error_cases == 1
    assert "TimeoutError" in report.outcomes[0].error


def test_runner_rejects_empty_dataset():
    dataset = RAGEvaluationDataset(
        dataset_name="empty-test",
        cases=[create_case()],
    )

    dataset.cases.clear()

    runner = RAGBenchmarkRunner(
        CallableRAGAdapter(lambda case: create_result())
    )

    try:
        asyncio.run(runner.run(dataset))
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_runner_respects_concurrency_configuration():
    active = 0
    maximum_active = 0

    async def pipeline(case):
        nonlocal active, maximum_active

        active += 1
        maximum_active = max(maximum_active, active)

        await asyncio.sleep(0.02)

        active -= 1

        return create_result()

    dataset = RAGEvaluationDataset(
        dataset_name="concurrency-test",
        cases=[
            RAGEvaluationCase(
                case_id=f"case-{index}",
                query=f"Question {index}",
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
            )
            for index in range(4)
        ],
    )

    runner = RAGBenchmarkRunner(
        CallableRAGAdapter(pipeline),
        RAGBenchmarkConfig(max_concurrency=2),
    )

    report = asyncio.run(
        runner.run(dataset)
    )

    assert report.total_cases == 4
    assert maximum_active <= 2
