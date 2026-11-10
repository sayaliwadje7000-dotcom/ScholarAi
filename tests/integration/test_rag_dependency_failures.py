from unittest.mock import MagicMock

import pytest

import app.api.rag_dependencies as rag_dependencies


@pytest.fixture(autouse=True)
def reset_dependency_cache():
    rag_dependencies.get_rag_service.cache_clear()
    yield
    rag_dependencies.get_rag_service.cache_clear()


def test_embedding_initialization_failure_does_not_cache_service(
    monkeypatch,
):
    def failing_embedding_service():
        raise RuntimeError("Embedding provider initialization failed.")

    monkeypatch.setattr(
        rag_dependencies,
        "EmbeddingService",
        failing_embedding_service,
    )

    with pytest.raises(
        RuntimeError,
        match="Embedding provider initialization failed",
    ):
        rag_dependencies.get_rag_service()

    assert rag_dependencies.get_rag_service.cache_info().currsize == 0


def test_retrieval_initialization_failure_does_not_cache_service(
    monkeypatch,
):
    monkeypatch.setattr(
        rag_dependencies,
        "EmbeddingService",
        lambda: MagicMock(),
    )

    def failing_retrieval_service(embedding_service):
        raise RuntimeError("Retrieval initialization failed.")

    monkeypatch.setattr(
        rag_dependencies,
        "RetrievalService",
        failing_retrieval_service,
    )

    with pytest.raises(
        RuntimeError,
        match="Retrieval initialization failed",
    ):
        rag_dependencies.get_rag_service()

    assert rag_dependencies.get_rag_service.cache_info().currsize == 0


def test_rag_service_initialization_failure_does_not_cache_service(
    monkeypatch,
):
    monkeypatch.setattr(
        rag_dependencies,
        "EmbeddingService",
        lambda: MagicMock(),
    )

    monkeypatch.setattr(
        rag_dependencies,
        "RetrievalService",
        lambda embedding_service: MagicMock(),
    )

    def failing_rag_service(retrieval_service):
        raise RuntimeError("RAG initialization failed.")

    monkeypatch.setattr(
        rag_dependencies,
        "RAGService",
        failing_rag_service,
    )

    with pytest.raises(
        RuntimeError,
        match="RAG initialization failed",
    ):
        rag_dependencies.get_rag_service()

    assert rag_dependencies.get_rag_service.cache_info().currsize == 0
