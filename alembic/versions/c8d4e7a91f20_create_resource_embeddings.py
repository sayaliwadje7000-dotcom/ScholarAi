"""
Create resource embeddings.

Revision ID: c8d4e7a91f20
Revises: b7c4e91a2d60

Creates independent vector storage for study resources.
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

from pgvector.sqlalchemy import VECTOR


revision: str = "c8d4e7a91f20"

down_revision: Union[
    str,
    Sequence[str],
    None
] = "b7c4e91a2d60"

branch_labels = None
depends_on = None

VECTOR_DIMENSIONS = 1536


def upgrade() -> None:

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
                "PostgreSQL pgvector extension is not activated."
            )

    op.create_table(
        "resource_embeddings",

        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),

        sa.Column(
            "resource_id",
            sa.Uuid(),
            nullable=False,
        ),

        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "model",
            sa.String(length=150),
            nullable=False,
        ),

        sa.Column(
            "model_version",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "dimensions",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "pipeline_version",
            sa.String(length=50),
            nullable=False,
            server_default="1.0.0",
        ),

        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),

        sa.Column(
            "embedding",
            VECTOR(VECTOR_DIMENSIONS),
            nullable=True,
        ),

        sa.Column(
            "error_code",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["study_resources.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "resource_id",
            "content_hash",
            "provider",
            "model",
            "model_version",
            "dimensions",
            "pipeline_version",
            name="uq_resource_embeddings_identity",
        ),

        sa.CheckConstraint(
            "dimensions > 0",
            name="ck_resource_embeddings_dimensions_positive",
        ),

        sa.CheckConstraint(
            """
            status IN (
                'pending',
                'ready',
                'failed',
                'stale'
            )
            """,
            name="ck_resource_embeddings_status",
        ),

        sa.CheckConstraint(
            """
            embedding IS NULL OR dimensions = 1536
            """,
            name="ck_resource_embeddings_vector_dimensions",
        ),
    )

    op.create_index(
        "ix_resource_embeddings_resource_id",
        "resource_embeddings",
        ["resource_id"],
    )

    op.create_index(
        "ix_resource_embeddings_status",
        "resource_embeddings",
        ["status"],
    )

    op.create_index(
        "ix_resource_embeddings_model_dimensions",
        "resource_embeddings",
        ["model", "dimensions"],
    )

    op.create_index(
        "ix_resource_embeddings_embedding_hnsw",
        "resource_embeddings",
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

    op.drop_index(
        "ix_resource_embeddings_embedding_hnsw",
        table_name="resource_embeddings",
    )

    op.drop_index(
        "ix_resource_embeddings_model_dimensions",
        table_name="resource_embeddings",
    )

    op.drop_index(
        "ix_resource_embeddings_status",
        table_name="resource_embeddings",
    )

    op.drop_index(
        "ix_resource_embeddings_resource_id",
        table_name="resource_embeddings",
    )

    op.drop_table("resource_embeddings")