
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievedChunkResponse,
)
from app.services.rag.rag_service import RAGService


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def document_id():
    return uuid.uuid4()


@pytest.fixture
def db():
    return Mock()


@pytest.fixture
def rag_request():
    return RetrievalRequest(
        query="Explain binary search",
        limit=5,
    )


@pytest.fixture
def retrieved_chunk(document_id):
    return RetrievedChunkResponse.model_construct(
        chunk_id=uuid.uuid4(),
        document_id=document_id,
        chunk_index=0,
        text="Binary search repeatedly divides a sorted search space.",
        page_numbers=[5],
        start_page=5,
        end_page=5,
        similarity=0.92,
        distance=0.08,
        provider="gemini",
        model="gemini-embedding-2",
        dimensions=1536,
        pipeline_version="1.0",
        chunking_version="1.0",
    )


@pytest.fixture
def safety_allowed(monkeypatch):
    monkeypatch.setattr(
        "app.services.rag.rag_service.evaluate_message",
        lambda message: SimpleNamespace(
            allowed=True,
            category="safe",
            response=None,
        ),
    )

    monkeypatch.setattr(
        "app.services.rag.rag_service.validate_output",
        lambda answer: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )


@pytest.mark.asyncio
async def test_safety_rejection_prevents_retrieval(
    db, user_id, rag_request, monkeypatch
):
    retrieval = Mock()
    retrieval.search = AsyncMock()

    llm = AsyncMock()

    monkeypatch.setattr(
        "app.services.rag.rag_service.evaluate_message",
        lambda message: SimpleNamespace(
            allowed=False,
            category="unsafe",
            response="Request rejected.",
        ),
    )

    service = RAGService(retrieval, llm)

    result = await service.ask(db, user_id, rag_request)

    assert result.answer == "Request rejected."
    assert result.total_retrieved == 0
    retrieval.search.assert_not_called()
    llm.assert_not_called()


@pytest.mark.asyncio
async def test_empty_retrieval_returns_insufficient_evidence(
    db, user_id, rag_request, safety_allowed
):
    retrieval = Mock()
    retrieval.search = AsyncMock(return_value=[])

    llm = AsyncMock()

    service = RAGService(retrieval, llm)

    result = await service.ask(db, user_id, rag_request)

    assert result.total_retrieved == 0
    assert result.grounded is False
    assert "could not find relevant information" in result.answer.lower()

    llm.assert_not_called()


@pytest.mark.asyncio
async def test_retrieved_context_is_passed_to_llm(
    db, user_id, rag_request, retrieved_chunk, safety_allowed
):
    retrieval = Mock()
    retrieval.search = AsyncMock(return_value=[retrieved_chunk])

    llm = AsyncMock(
        return_value="Binary search divides the search space."
    )

    service = RAGService(retrieval, llm)

    result = await service.ask(db, user_id, rag_request)

    llm.assert_awaited_once()

    prompt = llm.await_args.args[0]

    assert "Binary search" in prompt
    assert "document_content" in prompt
    assert "[EVIDENCE S1]" in prompt
    assert result.answer == "Binary search divides the search space."
@pytest.mark.asyncio
async def test_successful_generation_returns_retrieved_evidence(
    db, user_id, rag_request, retrieved_chunk, safety_allowed
):
    retrieval = Mock()
    retrieval.search = AsyncMock(return_value=[retrieved_chunk])

    llm = AsyncMock(
        return_value="Binary search is an efficient algorithm. [S1]"

    )

    service = RAGService(retrieval, llm)

    result = await service.ask(db, user_id, rag_request)

    assert result.total_retrieved == 1
    assert result.grounded is True
    assert len(result.retrieved_chunks) == 1

    assert (
        result.retrieved_chunks[0].document_id
        == retrieved_chunk.document_id
    )


@pytest.mark.asyncio
async def test_sensitive_generated_output_is_rejected(
    db, user_id, rag_request, retrieved_chunk, monkeypatch
):
    retrieval = Mock()
    retrieval.search = AsyncMock(return_value=[retrieved_chunk])

    llm = AsyncMock(return_value="Sensitive output")

    monkeypatch.setattr(
        "app.services.rag.rag_service.evaluate_message",
        lambda message: SimpleNamespace(
            allowed=True,
            category="safe",
            response=None,
        ),
    )

    monkeypatch.setattr(
        "app.services.rag.rag_service.validate_output",
        lambda answer: SimpleNamespace(
            allowed=False,
            response="Output blocked.",
        ),
    )

    service = RAGService(retrieval, llm)

    result = await service.ask(db, user_id, rag_request)

    assert result.answer == "Output blocked."
    assert result.grounded is False


@pytest.mark.asyncio
async def test_retrieval_uses_authenticated_user_id(
    db, user_id, rag_request, retrieved_chunk, safety_allowed
):
    retrieval = Mock()
    retrieval.search = AsyncMock(return_value=[retrieved_chunk])

    llm = AsyncMock(
        return_value="Answer based on retrieved evidence."
    )

    service = RAGService(retrieval, llm)

    await service.ask(db, user_id, rag_request)

    retrieval.search.assert_awaited_once_with(
        db=db,
        user_id=user_id,
        request=rag_request,
    )
