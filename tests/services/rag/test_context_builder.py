
import uuid

import pytest

from app.schemas.retrieval import RetrievedChunkResponse
from app.services.rag.context_builder import ContextBuilder


@pytest.fixture
def chunks():

    document_id = uuid.uuid4()

    return [
        RetrievedChunkResponse.model_construct(
            chunk_id=uuid.uuid4(),
            document_id=document_id,
            chunk_index=index,
            text=f"Academic evidence content for chunk {index}.",
            page_numbers=[index + 1],
            start_page=index + 1,
            end_page=index + 1,
            similarity=0.95 - index * 0.05,
            distance=0.05 + index * 0.05,
            provider="gemini",
            model="gemini-embedding-2",
            dimensions=1536,
            pipeline_version="1.0",
            chunking_version="1.0",
        )
        for index in range(5)
    ]


def test_context_builder_includes_retrieved_chunks(chunks):

    builder = ContextBuilder()

    result = builder.build(chunks)

    assert result.included_chunks == 5
    assert result.excluded_chunks == 0
    assert len(result.sources) == 5


def test_context_builder_respects_max_chunks(chunks):

    builder = ContextBuilder(max_chunks=2)

    result = builder.build(chunks)

    assert result.included_chunks == 2
    assert result.excluded_chunks == 3


def test_context_builder_respects_character_budget(chunks):

    builder = ContextBuilder(
        max_chunks=5,
        max_context_chars=500,
    )

    result = builder.build(chunks)

    assert result.total_characters <= 500
    assert len(result.context) <= 500


def test_context_builder_preserves_source_metadata(chunks):

    builder = ContextBuilder()

    result = builder.build(chunks)

    assert result.sources[0].source_id == "S1"
    assert result.sources[0].chunk_id == str(chunks[0].chunk_id)
    assert result.sources[0].document_id == str(chunks[0].document_id)
    assert result.sources[0].page_numbers == [1]


def test_context_builder_handles_large_chunks(chunks):

    chunks[0].text = "A" * 20000

    builder = ContextBuilder(
        max_chunks=5,
        max_context_chars=1000,
        max_chunk_chars=6000,
    )

    result = builder.build(chunks)

    assert result.total_characters <= 1000
    assert result.included_chunks >= 1
    assert "truncated" in result.context.lower()


def test_context_builder_rejects_invalid_configuration():

    with pytest.raises(ValueError):
        ContextBuilder(max_chunks=0)

    with pytest.raises(ValueError):
        ContextBuilder(max_context_chars=0)

    with pytest.raises(ValueError):
        ContextBuilder(max_chunk_chars=0)


def test_context_builder_handles_empty_results():

    builder = ContextBuilder()

    result = builder.build([])

    assert result.context == ""
    assert result.included_chunks == 0
    assert result.excluded_chunks == 0
    assert result.total_characters == 0
