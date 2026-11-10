import pytest

import app.api.rag_dependencies as rag_dependencies


@pytest.fixture(autouse=True)
def clear_rag_dependency_cache():
    rag_dependencies.get_rag_service.cache_clear()
    yield
    rag_dependencies.get_rag_service.cache_clear()


def test_rag_dependency_can_recover_after_initialization_failure(monkeypatch):
    attempts = {"embedding": 0}

    class FakeEmbeddingService:
        def __init__(self):
            attempts["embedding"] += 1

            if attempts["embedding"] == 1:
                raise RuntimeError(
                    "Temporary embedding initialization failure"
                )

    class FakeRetrievalService:
        def __init__(self, embedding_service):
            self.embedding_service = embedding_service

    class FakeRAGService:
        def __init__(self, retrieval_service):
            self.retrieval_service = retrieval_service

    monkeypatch.setattr(
        rag_dependencies,
        "EmbeddingService",
        FakeEmbeddingService,
    )
    monkeypatch.setattr(
        rag_dependencies,
        "RetrievalService",
        FakeRetrievalService,
    )
    monkeypatch.setattr(
        rag_dependencies,
        "RAGService",
        FakeRAGService,
    )

    with pytest.raises(
        RuntimeError,
        match="Temporary embedding initialization failure",
    ):
        rag_dependencies.get_rag_service()

    recovered_service = rag_dependencies.get_rag_service()

    assert isinstance(recovered_service, FakeRAGService)
    assert isinstance(
        recovered_service.retrieval_service,
        FakeRetrievalService,
    )
    assert attempts["embedding"] == 2


def test_recovered_rag_dependency_is_cached():
    first_service = rag_dependencies.get_rag_service()
    second_service = rag_dependencies.get_rag_service()

    assert first_service is second_service


def test_rag_dependency_cache_can_be_cleared():
    first_service = rag_dependencies.get_rag_service()

    rag_dependencies.get_rag_service.cache_clear()

    second_service = rag_dependencies.get_rag_service()

    assert first_service is not second_service
