import json
import uuid

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.core.chunking_config import ChunkingSettings

from app.services.document_chunking_service import (
    DocumentChunkingInputError,
    DocumentChunkingStorageError,
    chunk_document_pages,
    chunk_document_text,
    save_chunking_artifact,
)


@dataclass
class MockPage:
    page_number: int
    text: str


@pytest.fixture
def document_id():
    return str(uuid.uuid4())


@pytest.fixture
def pages():
    return [
        MockPage(
            page_number=1,
            text=(
                "Python is a programming language. "
                "It supports object-oriented programming. "
                "It is widely used in data science."
            ),
        ),
        MockPage(
            page_number=2,
            text=(
                "Machine learning is a field of artificial "
                "intelligence. It learns patterns from data."
            ),
        ),
    ]


def test_chunk_document_pages(document_id, pages):
    result = chunk_document_pages(
        document_id,
        pages,
        ChunkingSettings(
            chunk_size=60,
            chunk_overlap=10,
            minimum_chunk_size=10,
        ),
    )

    assert result.document_id == document_id
    assert result.chunk_count > 0
    assert len(result.chunks) == result.chunk_count


def test_chunk_indexes_are_sequential(document_id, pages):
    result = chunk_document_pages(
        document_id,
        pages,
        ChunkingSettings(
            chunk_size=60,
            chunk_overlap=10,
            minimum_chunk_size=10,
        ),
    )

    assert [
        chunk.chunk_index for chunk in result.chunks
    ] == list(range(result.chunk_count))


def test_chunk_metadata_is_populated(document_id, pages):
    result = chunk_document_pages(
        document_id,
        pages,
        ChunkingSettings(
            chunk_size=60,
            chunk_overlap=10,
            minimum_chunk_size=10,
        ),
    )

    for chunk in result.chunks:
        assert chunk.chunk_id
        assert chunk.document_id == document_id
        assert chunk.text
        assert chunk.character_count == len(chunk.text)
        assert chunk.word_count == len(chunk.text.split())
        assert chunk.page_numbers
        assert chunk.start_page <= chunk.end_page


def test_page_boundaries_are_preserved(document_id, pages):
    result = chunk_document_pages(
        document_id,
        pages,
        ChunkingSettings(
            chunk_size=60,
            chunk_overlap=10,
            minimum_chunk_size=10,
            preserve_page_boundaries=True,
        ),
    )

    for chunk in result.chunks:
        assert len(chunk.page_numbers) == 1


def test_chunk_ids_are_deterministic(document_id, pages):
    settings = ChunkingSettings(
        chunk_size=60,
        chunk_overlap=10,
        minimum_chunk_size=10,
    )

    first = chunk_document_pages(
        document_id,
        pages,
        settings,
    )

    second = chunk_document_pages(
        document_id,
        pages,
        settings,
    )

    assert [
        chunk.chunk_id for chunk in first.chunks
    ] == [
        chunk.chunk_id for chunk in second.chunks
    ]


def test_empty_pages_produce_no_chunks(document_id):
    result = chunk_document_pages(
        document_id,
        [
            MockPage(1, ""),
            MockPage(2, "   "),
        ],
    )

    assert result.chunk_count == 0
    assert result.chunks == []
    assert result.total_characters == 0
    assert result.total_words == 0


def test_non_contiguous_page_numbers_are_preserved(document_id):
    result = chunk_document_pages(
        document_id,
        [
            MockPage(3, "Third page content."),
            MockPage(8, "Eighth page content."),
        ],
    )

    assert result.chunks[0].page_numbers == [3]
    assert result.chunks[1].page_numbers == [8]


def test_invalid_document_id_is_rejected():
    with pytest.raises(DocumentChunkingInputError):
        chunk_document_pages(
            "invalid-id",
            [],
        )


def test_missing_document_id_is_rejected():
    with pytest.raises(DocumentChunkingInputError):
        chunk_document_pages(
            "",
            [],
        )


@pytest.mark.parametrize(
    "invalid_pages",
    [
        "invalid",
        [MockPage(0, "Text")],
        [MockPage(1, 123)],
        [MockPage(1, "First"), MockPage(1, "Duplicate")],
        [{"text": "Missing page number"}],
    ],
)
def test_invalid_pages_are_rejected(document_id, invalid_pages):
    with pytest.raises(DocumentChunkingInputError):
        chunk_document_pages(
            document_id,
            invalid_pages,
        )


def test_chunk_size_is_respected(document_id):
    text = " ".join(
        f"word{i}" for i in range(200)
    )

    result = chunk_document_pages(
        document_id,
        [MockPage(1, text)],
        ChunkingSettings(
            chunk_size=100,
            chunk_overlap=10,
            minimum_chunk_size=10,
        ),
    )

    assert all(
        len(chunk.text) <= 100
        for chunk in result.chunks
    )


def test_overlap_preserves_context(document_id):
    text = (
        "First sentence contains useful information. "
        "Second sentence contains more useful information. "
        "Third sentence contains additional useful information."
    )

    result = chunk_document_pages(
        document_id,
        [MockPage(1, text)],
        ChunkingSettings(
            chunk_size=65,
            chunk_overlap=15,
            minimum_chunk_size=5,
        ),
    )

    assert len(result.chunks) >= 2

    first = result.chunks[0].text
    second = result.chunks[1].text

    assert first[-10:] in second


def test_non_page_preserving_chunking(document_id):
    result = chunk_document_pages(
        document_id,
        [
            MockPage(1, "First page contains content."),
            MockPage(2, "Second page contains content."),
        ],
        ChunkingSettings(
            chunk_size=100,
            chunk_overlap=10,
            minimum_chunk_size=5,
            preserve_page_boundaries=False,
        ),
    )

    assert result.chunk_count == 1
    assert result.chunks[0].page_numbers == [1, 2]


def test_chunking_totals(document_id, pages):
    result = chunk_document_pages(
        document_id,
        pages,
        ChunkingSettings(
            chunk_size=500,
            chunk_overlap=50,
            minimum_chunk_size=10,
        ),
    )

    assert result.total_characters == sum(
        chunk.character_count
        for chunk in result.chunks
    )

    assert result.total_words == sum(
        chunk.word_count
        for chunk in result.chunks
    )


def test_save_chunking_artifact(
    document_id,
    pages,
    tmp_path,
):
    result = chunk_document_pages(
        document_id,
        pages,
    )

    path = save_chunking_artifact(
        result,
        tmp_path,
    )

    assert path.is_file()
    assert path.name == f"{document_id}_chunks.json"

    artifact = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert artifact["document_id"] == document_id
    assert artifact["chunk_count"] == result.chunk_count
    assert len(artifact["chunks"]) == result.chunk_count


def test_chunk_artifact_is_valid_json(
    document_id,
    pages,
    tmp_path,
):
    result = chunk_document_pages(
        document_id,
        pages,
    )

    path = save_chunking_artifact(
        result,
        tmp_path,
    )

    artifact = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert isinstance(artifact["chunks"], list)


def test_complete_chunking_workflow(
    document_id,
    pages,
    tmp_path,
):
    result, path = chunk_document_text(
        document_id=document_id,
        pages=pages,
        storage_root=tmp_path,
    )

    assert result.chunk_count > 0
    assert path.is_file()


def test_storage_rejects_invalid_result(tmp_path):
    with pytest.raises(DocumentChunkingInputError):
        save_chunking_artifact(
            None,
            tmp_path,
        )


def test_storage_failure_is_wrapped(
    document_id,
    pages,
    tmp_path,
):
    result = chunk_document_pages(
        document_id,
        pages,
    )

    # Use a regular file where the processed directory
    # would need to be created.
    storage_root = tmp_path / "blocked"
    storage_root.write_text("not a directory")

    with pytest.raises(DocumentChunkingStorageError):
        save_chunking_artifact(
            result,
            storage_root,
        )