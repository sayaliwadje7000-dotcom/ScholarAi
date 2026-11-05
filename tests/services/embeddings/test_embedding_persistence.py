from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.embeddings.embedding_persistence import (
    EmbeddingPersistenceService,
    EmbeddingPersistenceValidationError,
)
from app.services.embeddings.embedding_pipeline import ChunkEmbeddingOutcome
from app.schemas.embeddings import EmbeddingResult


DIMENSIONS = 1536

SETTINGS = SimpleNamespace(
    provider="gemini",
    model="gemini-embedding-2",
)


def make_embedding():
    return EmbeddingResult(
        vector=tuple([0.1] * DIMENSIONS),
        model="gemini-embedding-2",
        provider="gemini",
        dimensions=DIMENSIONS,
    )


def make_outcome(status="ready", embedding=None):
    return ChunkEmbeddingOutcome(
        chunk_id="chunk-001",
        content_hash="test-content-hash",
        status=status,
        embedding=(
            embedding
            if embedding is not None
            else make_embedding() if status == "ready" else None
        ),
        error_code="PROVIDER_ERROR" if status == "failed" else None,
    )


def make_chunk(content_hash="test-content-hash"):
    return SimpleNamespace(
        chunk_id="chunk-001",
        content_hash=content_hash,
    )


def make_result(value):
    """Create a predictable SQLAlchemy-like query result."""
    return SimpleNamespace(
        scalars=lambda: SimpleNamespace(
            first=lambda: value
        )
    )


def make_db():
    return MagicMock()


def make_service():
    service = EmbeddingPersistenceService.__new__(
        EmbeddingPersistenceService
    )
    service.settings = SETTINGS
    return service


def configure_database(db, chunk=None, existing=None):
    """
    First execute: fetch document chunk.
    Second execute: fetch existing embedding.
    """
    db.execute.side_effect = [
        make_result(chunk if chunk is not None else make_chunk()),
        make_result(existing),
    ]


def test_persists_new_embedding():
    db = make_db()
    configure_database(db)

    result = make_service().persist(
        db,
        [make_outcome()],
    )

    assert result.total == 1
    assert result.inserted == 1
    assert result.updated == 0
    assert result.failed == 0

    db.add.assert_called_once()
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_persists_failed_outcome():
    db = make_db()
    configure_database(db)

    result = make_service().persist(
        db,
        [make_outcome(status="failed")],
    )

    assert result.total == 1
    assert result.failed == 1
    assert result.inserted == 1

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_rejects_wrong_dimensions():
    db = make_db()

    invalid_embedding = EmbeddingResult(
        vector=tuple([0.1] * 768),
        model="gemini-embedding-2",
        provider="gemini",
        dimensions=768,
    )

    outcome = make_outcome(embedding=invalid_embedding)

    with pytest.raises(EmbeddingPersistenceValidationError):
        make_service().persist(db, [outcome])

    db.execute.assert_not_called()
    db.commit.assert_not_called()
    db.add.assert_not_called()


def test_rejects_missing_chunk():
    db = make_db()

    db.execute.return_value = make_result(None)

    with pytest.raises(EmbeddingPersistenceValidationError):
        make_service().persist(
            db,
            [make_outcome()],
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_rejects_content_hash_mismatch():
    db = make_db()

    wrong_chunk = make_chunk(
        content_hash="different-hash"
    )

    db.execute.return_value = make_result(wrong_chunk)

    with pytest.raises(EmbeddingPersistenceValidationError):
        make_service().persist(
            db,
            [make_outcome()],
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_rolls_back_database_failure():
    db = make_db()
    configure_database(db)

    db.flush.side_effect = RuntimeError("Database failure")

    with pytest.raises(RuntimeError, match="Database failure"):
        make_service().persist(
            db,
            [make_outcome()],
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_rejects_invalid_status():
    db = make_db()

    outcome = ChunkEmbeddingOutcome(
        chunk_id="chunk-001",
        content_hash="test-content-hash",
        status="pending",
    )

    with pytest.raises(EmbeddingPersistenceValidationError):
        make_service().persist(
            db,
            [outcome],
        )

    db.execute.assert_not_called()
    db.commit.assert_not_called()
    db.add.assert_not_called()