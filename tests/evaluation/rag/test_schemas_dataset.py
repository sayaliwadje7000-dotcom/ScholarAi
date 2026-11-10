import pytest
from pydantic import ValidationError

from app.evaluation.rag.schemas import (
    RAGBenchmarkCase,
    RAGBenchmarkDataset,
)
from app.evaluation.rag.dataset import RAGDatasetRegistry


def make_dataset(version="1.0"):
    return RAGBenchmarkDataset(
        dataset_name="rag-benchmark",
        version=version,
        cases=[
            RAGBenchmarkCase(
                case_id="case-1",
                query="Explain retrieval augmented generation.",
                expected_chunk_ids=["chunk-1"],
                reference_answer="RAG combines retrieval and generation.",
                required_terms=["retrieval", "generation"],
                expected_citation_source_ids=["source-1"],
            )
        ],
    )


def test_dataset_creation():
    dataset = make_dataset()
    assert dataset.dataset_name == "rag-benchmark"
    assert len(dataset.cases) == 1


def test_duplicate_case_ids_rejected():
    case = RAGBenchmarkCase(
        case_id="same",
        query="Question",
    )

    with pytest.raises(ValidationError):
        RAGBenchmarkDataset(
            dataset_name="invalid",
            cases=[case, case],
        )


def test_registry_register_and_get():
    registry = RAGDatasetRegistry()
    dataset = make_dataset()

    registry.register(dataset)

    assert registry.get(
        "rag-benchmark", "1.0"
    ) == dataset


def test_registry_rejects_duplicate_version():
    registry = RAGDatasetRegistry()
    dataset = make_dataset()

    registry.register(dataset)

    with pytest.raises(ValueError):
        registry.register(dataset)


def test_registry_lists_versions():
    registry = RAGDatasetRegistry()

    registry.register(make_dataset("1.0"))
    registry.register(make_dataset("2.0"))

    assert registry.list_versions("rag-benchmark") == [
        "1.0",
        "2.0",
    ]
