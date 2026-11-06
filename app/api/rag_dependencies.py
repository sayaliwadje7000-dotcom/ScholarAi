from functools import lru_cache

from app.services.embeddings.embedding_service import EmbeddingService

from app.services.retrieval_service import RetrievalService

from app.services.rag.rag_service import RAGService


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """
    Construct and reuse the RAG service and its dependencies.

    The embedding provider is initialized lazily when the
    first RAG request requires the service.
    """

    embedding_service = EmbeddingService()

    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
    )

    return RAGService(
        retrieval_service=retrieval_service,
    )