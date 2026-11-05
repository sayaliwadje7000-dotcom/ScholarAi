import asyncio

import pytest

from app.core.embedding_config import EmbeddingSettings

from app.schemas.embeddings import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTask,
)

from app.services.embeddings.embedding_service import (
    EmbeddingService,
)


class FakeProvider:

    def __init__(self):
        self.requests = []
        self.active = 0
        self.max_active = 0
        self.closed = False

    async def embed(self, request: EmbeddingRequest):

        self.requests.append(request)

        self.active += 1
        self.max_active = max(
            self.max_active,
            self.active
        )

        try:
            await asyncio.sleep(0.01)

            return EmbeddingResult(
                vector=(0.1,) * 768,
                model="test-model",
                provider="test",
                dimensions=768,
            )

        finally:
            self.active -= 1

    async def close(self):
        self.closed = True


@pytest.fixture
def settings():
    return EmbeddingSettings(
        dimensions=768,
        max_concurrent_requests=2,
    )


@pytest.mark.asyncio
async def test_document_embedding(settings):

    provider = FakeProvider()

    service = EmbeddingService(
        provider=provider,
        settings=settings,
    )

    result = await service.embed_document(
        "Introduction to artificial intelligence"
    )

    assert result.dimensions == 768

    assert (
        provider.requests[0].task
        == EmbeddingTask.DOCUMENT
    )


@pytest.mark.asyncio
async def test_query_embedding(settings):

    provider = FakeProvider()

    service = EmbeddingService(
        provider=provider,
        settings=settings,
    )

    await service.embed_query(
        "What is artificial intelligence?"
    )

    assert (
        provider.requests[0].task
        == EmbeddingTask.QUERY
    )


@pytest.mark.asyncio
async def test_batch_order_preserved(settings):

    provider = FakeProvider()

    service = EmbeddingService(
        provider=provider,
        settings=settings,
    )

    texts = [
        "First document",
        "Second document",
        "Third document",
    ]

    results = await service.embed_documents(texts)

    assert len(results) == 3

    assert [
        request.text
        for request in provider.requests
    ] == texts


@pytest.mark.asyncio
async def test_concurrency_is_bounded(settings):

    provider = FakeProvider()

    service = EmbeddingService(
        provider=provider,
        settings=settings,
    )

    await service.embed_documents(
        [f"Document {i}" for i in range(10)]
    )

    assert provider.max_active <= 2


@pytest.mark.asyncio
async def test_empty_batch_rejected(settings):

    service = EmbeddingService(
        provider=FakeProvider(),
        settings=settings,
    )

    with pytest.raises(ValueError):
        await service.embed_documents([])


@pytest.mark.asyncio
async def test_service_close(settings):

    provider = FakeProvider()

    service = EmbeddingService(
        provider=provider,
        settings=settings,
    )

    await service.close()

    assert provider.closed