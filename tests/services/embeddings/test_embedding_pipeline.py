from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.schemas.embeddings import EmbeddingResult
from app.services.embeddings.embedding_pipeline import (
    EmbeddingPipeline,
    EmbeddingPipelineInputError,
)
from app.services.embeddings.metadata import compute_content_hash


@dataclass
class FakeChunk:
    chunk_id: str
    text: str
    content_hash: str


def make_chunk(text: str, chunk_id: str = "chunk-1"):
    return FakeChunk(
        chunk_id=chunk_id,
        text=text,
        content_hash=compute_content_hash(text),
    )


class FakeEmbeddingService:

    def __init__(self, settings=None, fail_on=None):
        self.settings = settings or SimpleNamespace(
            provider="gemini",
            model="gemini-embedding-2",
            dimensions=3,
        )

        self.fail_on = fail_on or set()
        self.calls = []

    async def embed_document(self, text):
        self.calls.append(text)

        if text in self.fail_on:
            raise RuntimeError("Simulated provider failure.")

        return EmbeddingResult(
            vector=(0.1, 0.2, 0.3),
            model=self.settings.model,
            provider=self.settings.provider,
            dimensions=self.settings.dimensions,
        )


@pytest.fixture
def service():
    return FakeEmbeddingService()


@pytest.fixture
def pipeline(service):
    return EmbeddingPipeline(
        embedding_service=service,
        batch_size=2,
    )


@pytest.mark.asyncio
async def test_generate_embeddings_successfully(pipeline):
    chunks = [
        make_chunk("Machine learning", "chunk-1"),
        make_chunk("Deep learning", "chunk-2"),
    ]

    result = await pipeline.generate(chunks)

    assert result.total_chunks == 2
    assert result.successful_chunks == 2
    assert result.failed_chunks == 0

    assert all(
        outcome.status == "ready"
        for outcome in result.outcomes
    )


@pytest.mark.asyncio
async def test_empty_chunk_collection_returns_empty_result(pipeline):
    result = await pipeline.generate([])

    assert result.total_chunks == 0
    assert result.successful_chunks == 0
    assert result.failed_chunks == 0
    assert result.outcomes == ()


@pytest.mark.asyncio
async def test_pipeline_preserves_input_order(pipeline):
    chunks = [
        make_chunk("First", "chunk-1"),
        make_chunk("Second", "chunk-2"),
        make_chunk("Third", "chunk-3"),
    ]

    result = await pipeline.generate(chunks)

    assert [
        outcome.chunk_id
        for outcome in result.outcomes
    ] == [
        "chunk-1",
        "chunk-2",
        "chunk-3",
    ]


@pytest.mark.asyncio
async def test_pipeline_processes_all_batches(pipeline):
    chunks = [
        make_chunk(f"Text {index}", f"chunk-{index}")
        for index in range(5)
    ]

    result = await pipeline.generate(chunks)

    assert result.total_chunks == 5
    assert result.successful_chunks == 5


@pytest.mark.asyncio
async def test_individual_failure_does_not_stop_pipeline():
    service = FakeEmbeddingService(
        fail_on={"Bad content"}
    )

    pipeline = EmbeddingPipeline(service, batch_size=3)

    chunks = [
        make_chunk("Good content", "chunk-1"),
        make_chunk("Bad content", "chunk-2"),
        make_chunk("More good content", "chunk-3"),
    ]

    result = await pipeline.generate(chunks)

    assert result.total_chunks == 3
    assert result.successful_chunks == 2
    assert result.failed_chunks == 1

    assert result.outcomes[1].status == "failed"
    assert result.outcomes[1].error_code == "RuntimeError"


def test_invalid_batch_size_rejected(service):
    with pytest.raises(ValueError):
        EmbeddingPipeline(service, batch_size=0)


@pytest.mark.asyncio
async def test_duplicate_chunk_ids_rejected(pipeline):
    chunks = [
        make_chunk("First content", "duplicate"),
        make_chunk("Second content", "duplicate"),
    ]

    with pytest.raises(EmbeddingPipelineInputError):
        await pipeline.generate(chunks)


@pytest.mark.asyncio
async def test_content_hash_mismatch_rejected(pipeline):
    chunk = FakeChunk(
        chunk_id="chunk-1",
        text="Original content",
        content_hash="incorrect-hash",
    )

    with pytest.raises(EmbeddingPipelineInputError):
        await pipeline.generate([chunk])


@pytest.mark.asyncio
async def test_empty_chunk_text_rejected(pipeline):
    chunk = FakeChunk(
        chunk_id="chunk-1",
        text=" ",
        content_hash=compute_content_hash(" "),
    )

    with pytest.raises(EmbeddingPipelineInputError):
        await pipeline.generate([chunk])


@pytest.mark.asyncio
async def test_invalid_chunk_identifier_rejected(pipeline):
    chunk = make_chunk("Valid text", "")

    with pytest.raises(EmbeddingPipelineInputError):
        await pipeline.generate([chunk])


@pytest.mark.asyncio
async def test_embedding_dimension_mismatch_is_failed():
    settings = SimpleNamespace(
        provider="gemini",
        model="gemini-embedding-2",
        dimensions=4,
    )

    service = FakeEmbeddingService(settings=settings)

    pipeline = EmbeddingPipeline(service)

    result = await pipeline.generate([
        make_chunk("Test content")
    ])

    assert result.failed_chunks == 1
    assert result.outcomes[0].status == "failed"
    assert result.outcomes[0].error_code == "ValueError"


@pytest.mark.asyncio
async def test_embedding_model_mismatch_is_failed():
    service = FakeEmbeddingService()

    async def invalid_model(text):
        return EmbeddingResult(
            vector=(0.1, 0.2, 0.3),
            model="different-model",
            provider="gemini",
            dimensions=3,
        )

    service.embed_document = invalid_model

    pipeline = EmbeddingPipeline(service)

    result = await pipeline.generate([
        make_chunk("Test content")
    ])

    assert result.failed_chunks == 1
    assert result.outcomes[0].error_code == "ValueError"


@pytest.mark.asyncio
async def test_success_rate_calculation(pipeline):
    chunks = [
        make_chunk("Good", "chunk-1"),
        make_chunk("Another good", "chunk-2"),
    ]

    result = await pipeline.generate(chunks)

    assert result.success_rate == 1.0


@pytest.mark.asyncio
async def test_pipeline_reports_provider_metadata(pipeline):
    result = await pipeline.generate([
        make_chunk("Test content")
    ])

    assert result.provider == "gemini"
    assert result.model == "gemini-embedding-2"
    assert result.dimensions == 3