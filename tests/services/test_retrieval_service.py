from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.retrieval import RetrievalRequest

from app.services.retrieval_service import (
    RetrievalService,
    DocumentAccessDeniedError,
)


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def document_ids() -> list[uuid.UUID]:
    return [uuid.uuid4(), uuid.uuid4()]


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def embedding_service():
    service = MagicMock()
    service.embed_query = AsyncMock()

    embedding_result = MagicMock()
    embedding_result.vector = [0.1] * 1536

    service.embed_query.return_value = embedding_result

    return service


@pytest.fixture
def semantic_search_service():
    return MagicMock()


@pytest.fixture
def retrieval_service(
    embedding_service,
    semantic_search_service,
):
    return RetrievalService(
        embedding_service=embedding_service,
        semantic_search_service=semantic_search_service,
    )


def mock_owned_documents(db, owned_ids):
    result = MagicMock()
    result.scalars.return_value.all.return_value = owned_ids
    db.execute.return_value = result


@pytest.mark.asyncio
async def test_retrieval_uses_only_owned_documents(
    retrieval_service,
    db,
    embedding_service,
    semantic_search_service,
    user_id,
    document_ids,
):
    mock_owned_documents(db, document_ids)

    expected_results = [MagicMock()]
    semantic_search_service.search.return_value = expected_results

    request = RetrievalRequest(
        query="Explain machine learning",
    )

    results = await retrieval_service.search(
        db=db,
        user_id=user_id,
        request=request,
    )

    assert results == expected_results

    embedding_service.embed_query.assert_awaited_once_with(
        "Explain machine learning"
    )

    semantic_search_service.search.assert_called_once()

    search_kwargs = semantic_search_service.search.call_args.kwargs

    assert search_kwargs["db"] == db
    assert search_kwargs["query_vector"] == [0.1] * 1536
    assert search_kwargs["document_ids"] == document_ids


@pytest.mark.asyncio
async def test_retrieval_rejects_unowned_document(
    retrieval_service,
    db,
    user_id,
):
    requested_document_id = uuid.uuid4()

    mock_owned_documents(db, [])

    request = RetrievalRequest(
        query="Explain machine learning",
        document_id=requested_document_id,
    )

    with pytest.raises(DocumentAccessDeniedError):
        await retrieval_service.search(
            db=db,
            user_id=user_id,
            request=request,
        )


@pytest.mark.asyncio
async def test_retrieval_rejects_mixed_owned_and_unowned_documents(
    retrieval_service,
    db,
    user_id,
    document_ids,
):
    owned_document_id = document_ids[0]
    unowned_document_id = uuid.uuid4()

    mock_owned_documents(
        db,
        [owned_document_id],
    )

    request = RetrievalRequest(
        query="Explain machine learning",
        document_ids=[
            owned_document_id,
            unowned_document_id,
        ],
    )

    with pytest.raises(DocumentAccessDeniedError):
        await retrieval_service.search(
            db=db,
            user_id=user_id,
            request=request,
        )


@pytest.mark.asyncio
async def test_retrieval_handles_user_with_no_documents(
    retrieval_service,
    db,
    embedding_service,
    semantic_search_service,
    user_id,
):
    mock_owned_documents(db, [])

    request = RetrievalRequest(
        query="Explain artificial intelligence",
    )

    results = await retrieval_service.search(
        db=db,
        user_id=user_id,
        request=request,
    )

    assert results == []

    embedding_service.embed_query.assert_not_awaited()
    semantic_search_service.search.assert_not_called()


def test_retrieval_rejects_empty_document_filter():

    with pytest.raises(ValueError):
        RetrievalRequest(
            query="Explain artificial intelligence",
            document_ids=[],
        )


@pytest.mark.asyncio
async def test_retrieval_passes_multiple_owned_documents(
    retrieval_service,
    db,
    user_id,
    document_ids,
    semantic_search_service,
):
    mock_owned_documents(db, document_ids)

    semantic_search_service.search.return_value = []

    request = RetrievalRequest(
        query="Explain neural networks",
        document_ids=document_ids,
    )

    await retrieval_service.search(
        db=db,
        user_id=user_id,
        request=request,
    )

    search_kwargs = semantic_search_service.search.call_args.kwargs

    assert set(search_kwargs["document_ids"]) == set(document_ids)


@pytest.mark.asyncio
async def test_retrieval_does_not_search_when_access_is_denied(
    retrieval_service,
    db,
    embedding_service,
    semantic_search_service,
    user_id,
):
    mock_owned_documents(db, [])

    request = RetrievalRequest(
        query="Explain neural networks",
        document_id=uuid.uuid4(),
    )

    with pytest.raises(DocumentAccessDeniedError):
        await retrieval_service.search(
            db=db,
            user_id=user_id,
            request=request,
        )

    embedding_service.embed_query.assert_not_awaited()
    semantic_search_service.search.assert_not_called()