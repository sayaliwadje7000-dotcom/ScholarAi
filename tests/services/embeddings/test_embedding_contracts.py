import pytest

from app.schemas.embeddings import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTask,
)


def test_valid_document_request():
    request = EmbeddingRequest(
        text="Introduction to machine learning.",
        task=EmbeddingTask.DOCUMENT,
    )

    assert request.task == EmbeddingTask.DOCUMENT


def test_empty_request_rejected():
    with pytest.raises(ValueError):
        EmbeddingRequest(
            text="   ",
            task=EmbeddingTask.DOCUMENT,
        )


def test_invalid_task_rejected():
    with pytest.raises(TypeError):
        EmbeddingRequest(
            text="Example",
            task="invalid",
        )


def test_embedding_result():
    result = EmbeddingResult(
        vector=(0.1, 0.2, 0.3),
        model="test-model",
        provider="test",
        dimensions=3,
    )

    assert result.dimensions == 3


def test_dimension_mismatch_rejected():
    with pytest.raises(ValueError):
        EmbeddingResult(
            vector=(0.1, 0.2),
            model="test-model",
            provider="test",
            dimensions=3,
        )