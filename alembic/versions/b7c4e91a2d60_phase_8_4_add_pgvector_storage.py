"""phase_8_4_add_pgvector_storage

Revision ID: b7c4e91a2d60
Revises: 06b0f8605b90

Adds pgvector storage and an HNSW cosine index.
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

from pgvector.sqlalchemy import VECTOR


revision: str = "b7c4e91a2d60"
down_revision: Union[str, Sequence[str], None] = "06b0f8605b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VECTOR_DIMENSIONS = 1536


def upgrade() -> None:
    """Add pgvector storage infrastructure."""

    # Offline mode generates SQL without connecting to PostgreSQL.
    # Validate the extension only when a live connection exists.
    if not context.is_offline_mode():
        connection = op.get_bind()

        extension_exists = connection.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_extension
                    WHERE extname = 'vector'
                )
                """
            )
        ).scalar_one()

        if not extension_exists:
            raise RuntimeError(
                "PostgreSQL pgvector extension is not activated. "
                "A database administrator must run "
                "'CREATE EXTENSION vector;' before this migration."
            )

    op.add_column(
        "chunk_embeddings",
        sa.Column(
            "embedding",
            VECTOR(VECTOR_DIMENSIONS),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_chunk_embeddings_vector_dimensions",
        "chunk_embeddings",
        "embedding IS NULL OR dimensions = 1536",
    )

    op.create_index(
        "ix_chunk_embeddings_embedding_hnsw",
        "chunk_embeddings",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={
            "m": 16,
            "ef_construction": 64,
        },
        postgresql_ops={
            "embedding": "vector_cosine_ops",
        },
        postgresql_where=sa.text(
            "embedding IS NOT NULL AND status = 'ready'"
        ),
    )


def downgrade() -> None:
    """Remove Phase 8.4 objects without dropping the extension."""

    op.drop_index(
        "ix_chunk_embeddings_embedding_hnsw",
        table_name="chunk_embeddings",
    )

    op.drop_constraint(
        "ck_chunk_embeddings_vector_dimensions",
        "chunk_embeddings",
        type_="check",
    )

    op.drop_column(
        "chunk_embeddings",
        "embedding",
    )