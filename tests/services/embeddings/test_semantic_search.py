from types import SimpleNamespace
from unittest.mock import MagicMock

import uuid
import pytest

from app.services.embeddings.semantic_search import (
    SemanticSearchService,
    SemanticSearchValidationError,
    DATABASE_VECTOR_DIMENSIONS,
)


def make_service():
    return SemanticSearchService()


def make_vector():
    return [0.1] * DATABASE_VECTOR_DIMENSIONS


def make_row(distance=0.15):

    chunk = SimpleNamespace(
        chunk_id="chunk-001",
        document_id=uuid.uuid4(),
        chunk_index=0,
        text="Artificial intelligence and machine learning.",
        page_numbers=[1, 2],
        start_page=1,
        end_page=2,
        chunking_version="1.0",
    )

    embedding = SimpleNamespace(
        provider="gemini",
        model="gemini-embedding-2",
        dimensions=1536,
        pipeline_version="1.0.0",
    )

    return chunk, embedding, distance


def make_db(rows=None):
    db = MagicMock()
    db.execute.return_value.all.return_value = rows or []
    return db


def test_empty_search_results():
    db = make_db()

    results = make_service().search(
        db,
        make_vector(),
    )

    assert results == []
    db.execute.assert_called_once()


def test_returns_ranked_search_results():
    db = make_db([
        make_row(0.10),
        make_row(0.25),
        make_row(0.40),
    ])

    results = make_service().search(
        db,
        make_vector(),
    )

    assert len(results) == 3
    assert results[0].similarity == pytest.approx(0.90)
    assert results[1].similarity == pytest.approx(0.75)
    assert results[2].similarity == pytest.approx(0.60)


def test_returns_chunk_metadata():
    db = make_db([make_row()])

    results = make_service().search(
        db,
        make_vector(),
    )

    result = results[0]

    assert result.chunk_id == "chunk-001"
    assert isinstance(result.document_id, uuid.UUID)
    assert result.chunk_index == 0
    assert result.page_numbers == [1, 2]
    assert result.provider == "gemini"
    assert result.model == "gemini-embedding-2"


def test_rejects_wrong_vector_dimensions():
    db = make_db()

    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            db,
            [0.1] * 768,
        )


@pytest.mark.parametrize(
    "invalid_value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        "invalid",
        True,
    ],
)
def test_rejects_invalid_vector_values(invalid_value):
    vector = make_vector()
    vector[0] = invalid_value

    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            vector,
        )


def test_rejects_string_as_vector():
    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            "invalid",
        )


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_rejects_invalid_limits(limit):
    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            make_vector(),
            limit=limit,
        )


def test_rejects_boolean_limit():
    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            make_vector(),
            limit=True,
        )


@pytest.mark.parametrize(
    "threshold",
    [-1.1, 1.1, float("nan"), float("inf")],
)
def test_rejects_invalid_similarity_threshold(threshold):
    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            make_vector(),
            min_similarity=threshold,
        )


def test_rejects_non_uuid_document_id():
    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            make_vector(),
            document_id="invalid-document-id",
        )


def test_rejects_both_document_filters():
    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            make_vector(),
            document_id=uuid.uuid4(),
            document_ids=[uuid.uuid4()],
        )


def test_rejects_duplicate_document_ids():
    document_id = uuid.uuid4()

    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            make_vector(),
            document_ids=[
                document_id,
                document_id,
            ],
        )


def test_rejects_non_uuid_document_ids():
    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            make_vector(),
            document_ids=["invalid-document-id"],
        )


def test_rejects_empty_document_ids():
    with pytest.raises(SemanticSearchValidationError):
        make_service().search(
            make_db(),
            make_vector(),
            document_ids=[],
        )


def test_rejects_invalid_vector_dimensions_configuration():
    with pytest.raises(SemanticSearchValidationError):
        SemanticSearchService(
            vector_dimensions=768,
        )


def test_rejects_invalid_limit_configuration():
    with pytest.raises(SemanticSearchValidationError):
        SemanticSearchService(
            default_limit=20,
            max_limit=10,
        )


def test_search_accepts_document_filter():
    db = make_db()
    document_id = uuid.uuid4()

    make_service().search(
        db,
        make_vector(),
        document_id=document_id,
    )

    db.execute.assert_called_once()


def test_search_accepts_metadata_filters():
    db = make_db()

    document_ids = [
        uuid.uuid4(),
        uuid.uuid4(),
    ]

    make_service().search(
        db,
        make_vector(),
        document_ids=document_ids,
        chunking_version="1.0",
        provider="gemini",
        model="gemini-embedding-2",
        pipeline_version="1.0.0",
        min_similarity=0.70,
    )

    db.execute.assert_called_once()