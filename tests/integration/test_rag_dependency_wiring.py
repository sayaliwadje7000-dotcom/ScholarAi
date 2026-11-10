from unittest.mock import MagicMock

import pytest

import app.api.rag_dependencies as rag_dependencies


@pytest.fixture(autouse=True)
def clear_rag_service_cache():
    rag_dependencies.get_rag_service.cache_clear()
    yield
    rag_dependencies.get_rag_service.cache_clear()


def test_rag_dependency_factory_connects_all_components(monkeypatch):
    embedding_instance = MagicMock()
    retrieval_instance = MagicMock()
    rag_instance = MagicMock()

    class FakeEmbeddingService:
        def __init__(self):
            pass

    class FakeRetrievalService:
        def __init__(self, embedding_service):
            self.embedding_service = embedding_service

    class FakeRAGService:
        def __init__(self, retrieval_service):
            self.retrieval_service = retrieval_service

    def create_embedding_service():
        return embedding_instance

    def create_retrieval_service(embedding_service):
        assert embedding_service is embedding_instance
        return retrieval_instance

    def create_rag_service(retrieval_service):
        assert retrieval_service is retrieval_instance
        return rag_instance

    monkeypatch.setattr(
        rag_dependencies,
        "EmbeddingService",
        create_embedding_service,
    )

    monkeypatch.setattr(
        rag_dependencies,
        "RetrievalService",
        create_retrieval_service,
    )

    monkeypatch.setattr(
        rag_dependencies,
        "RAGService",
        create_rag_service,
    )

    result = rag_dependencies.get_rag_service()

    assert result is rag_instance


def test_rag_dependency_factory_reuses_cached_instance(monkeypatch):
    calls = {
        "embedding": 0,
        "retrieval": 0,
        "rag": 0,
    }

    embedding_instance = MagicMock()
    retrieval_instance = MagicMock()
    rag_instance = MagicMock()

    def create_embedding_service():
        calls["embedding"] += 1
        return embedding_instance

    def create_retrieval_service(embedding_service):
        calls["retrieval"] += 1
        assert embedding_service is embedding_instance
        return retrieval_instance

    def create_rag_service(retrieval_service):
        calls["rag"] += 1
        assert retrieval_service is retrieval_instance
        return rag_instance

    monkeypatch.setattr(
        rag_dependencies,
        "EmbeddingService",
        create_embedding_service,
    )

    monkeypatch.setattr(
        rag_dependencies,
        "RetrievalService",
        create_retrieval_service,
    )

    monkeypatch.setattr(
        rag_dependencies,
        "RAGService",
        create_rag_service,
    )

    first = rag_dependencies.get_rag_service()
    second = rag_dependencies.get_rag_service()

    assert first is second
    assert first is rag_instance

    assert calls == {
        "embedding": 1,
        "retrieval": 1,
        "rag": 1,
    }


def test_rag_dependency_cache_clear_rebuilds_service(monkeypatch):
    created_instances = []

    def create_embedding_service():
        instance = MagicMock()
        created_instances.append(instance)
        return instance

    def create_retrieval_service(embedding_service):
        return MagicMock(
            embedding_service=embedding_service,
        )

    def create_rag_service(retrieval_service):
        return MagicMock(
            retrieval_service=retrieval_service,
        )

    monkeypatch.setattr(
        rag_dependencies,
        "EmbeddingService",
        create_embedding_service,
    )

    monkeypatch.setattr(
        rag_dependencies,
        "RetrievalService",
        create_retrieval_service,
    )

    monkeypatch.setattr(
        rag_dependencies,
        "RAGService",
        create_rag_service,
    )

    first = rag_dependencies.get_rag_service()

    rag_dependencies.get_rag_service.cache_clear()

    second = rag_dependencies.get_rag_service()

    assert first is not second
    assert len(created_instances) == 2
