import pytest

from app.services.embeddings.metadata import (
    compute_content_hash,
)


def test_content_hash_is_deterministic():
    text = "Machine learning fundamentals"

    assert compute_content_hash(text) == compute_content_hash(text)


def test_content_hash_is_sha256():
    result = compute_content_hash("ScholarAI")

    assert len(result) == 64


def test_different_content_has_different_hash():
    first = compute_content_hash("Document A")
    second = compute_content_hash("Document B")

    assert first != second


def test_empty_content_rejected():
    with pytest.raises(ValueError):
        compute_content_hash("")


def test_invalid_content_type_rejected():
    with pytest.raises(TypeError):
        compute_content_hash(123)