import runpy
from pathlib import Path

import pytest
from pgvector.sqlalchemy import VECTOR

from app.models.chunk_embedding import ChunkEmbedding
from app.models.document_chunk import DocumentChunk


VECTOR_DIMENSIONS = 1536

HNSW_INDEX_NAME = "ix_chunk_embeddings_embedding_hnsw"


def get_embedding_index():
    return next(
        (
            index
            for index in ChunkEmbedding.__table__.indexes
            if index.name == HNSW_INDEX_NAME
        ),
        None,
    )


def test_embedding_column_uses_pgvector_type():
    column = ChunkEmbedding.__table__.columns["embedding"]

    assert isinstance(column.type, VECTOR)


def test_embedding_column_has_1536_dimensions():
    column = ChunkEmbedding.__table__.columns["embedding"]

    assert column.type.dim == VECTOR_DIMENSIONS


def test_embedding_column_is_nullable():
    column = ChunkEmbedding.__table__.columns["embedding"]

    assert column.nullable is True


def test_hnsw_index_is_registered():
    index = get_embedding_index()

    assert index is not None


def test_hnsw_index_uses_correct_method():
    index = get_embedding_index()

    assert index.dialect_options["postgresql"]["using"] == "hnsw"


def test_hnsw_index_uses_cosine_operator():
    index = get_embedding_index()

    operators = index.dialect_options["postgresql"]["ops"]

    assert operators["embedding"] == "vector_cosine_ops"


def test_hnsw_index_parameters():
    index = get_embedding_index()

    parameters = index.dialect_options["postgresql"]["with"]

    assert parameters["m"] == 16
    assert parameters["ef_construction"] == 64


def test_hnsw_index_has_partial_predicate():
    index = get_embedding_index()

    predicate = str(
        index.dialect_options["postgresql"]["where"]
    )

    assert "embedding IS NOT NULL" in predicate
    assert "status = 'ready'" in predicate


def test_vector_dimension_check_constraint_exists():
    constraints = {
        constraint.name: constraint
        for constraint in ChunkEmbedding.__table__.constraints
    }

    constraint = constraints.get(
        "ck_chunk_embeddings_vector_dimensions"
    )

    assert constraint is not None

    expression = str(constraint.sqltext)

    assert "embedding IS NULL" in expression
    assert "dimensions = 1536" in expression


def test_embedding_status_constraint_exists():
    constraints = {
        constraint.name: constraint
        for constraint in ChunkEmbedding.__table__.constraints
    }

    assert "ck_chunk_embeddings_status" in constraints


def test_embedding_relationship_configuration():
    relationship = ChunkEmbedding.chunk.property

    assert relationship.back_populates == "embeddings"


def test_document_chunk_embedding_relationship_configuration():
    relationship = DocumentChunk.embeddings.property

    assert relationship.back_populates == "chunk"
    assert relationship.cascade.delete_orphan


def test_phase_8_4_migration_revision_chain():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "b7c4e91a2d60_phase_8_4_add_pgvector_storage.py"
    )

    assert migration_path.exists()

    migration = runpy.run_path(str(migration_path))

    assert migration["revision"] == "b7c4e91a2d60"
    assert migration["down_revision"] == "06b0f8605b90"