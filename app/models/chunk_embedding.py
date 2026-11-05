from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
    func,
)
from sqlalchemy.orm import relationship

from pgvector.sqlalchemy import VECTOR

from app.database.base import Base


VECTOR_DIMENSIONS = 1536


class ChunkEmbedding(Base):
    """
    Stores versioned document chunk embeddings.

    Embedding metadata and vector storage are maintained together.
    A vector is nullable because pending and failed records do not
    necessarily have a generated embedding.
    """

    __tablename__ = "chunk_embeddings"

    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "content_hash",
            "provider",
            "model",
            "model_version",
            "dimensions",
            "pipeline_version",
            name="uq_chunk_embeddings_identity",
        ),

        CheckConstraint(
            "dimensions > 0",
            name="ck_chunk_embeddings_dimensions_positive",
        ),

        CheckConstraint(
            "status IN ('pending', 'ready', 'failed', 'stale')",
            name="ck_chunk_embeddings_status",
        ),

        CheckConstraint(
            "embedding IS NULL OR dimensions = 1536",
            name="ck_chunk_embeddings_vector_dimensions",
        ),

        Index(
            "ix_chunk_embeddings_chunk_id",
            "chunk_id",
        ),

        Index(
            "ix_chunk_embeddings_model_dimensions",
            "model",
            "dimensions",
        ),

        Index(
            "ix_chunk_embeddings_status",
            "status",
        ),

        Index(
            "ix_chunk_embeddings_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={
                "m": 16,
                "ef_construction": 64,
            },
            postgresql_ops={
                "embedding": "vector_cosine_ops",
            },
            postgresql_where=text(
                "embedding IS NOT NULL AND status = 'ready'"
            ),
        ),
    )

    id = Column(
        __import__("sqlalchemy").Uuid(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    chunk_id = Column(
        String(64),
        ForeignKey(
            "document_chunks.chunk_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    content_hash = Column(
        String(64),
        nullable=False,
    )

    provider = Column(
        String(50),
        nullable=False,
    )

    model = Column(
        String(150),
        nullable=False,
    )

    model_version = Column(
        String(100),
        nullable=False,
        default="unspecified",
    )

    dimensions = Column(
        Integer,
        nullable=False,
    )

    pipeline_version = Column(
        String(50),
        nullable=False,
        default="1.0",
    )

    status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    # Phase 8.4: actual pgvector storage.
    embedding = Column(
        VECTOR(VECTOR_DIMENSIONS),
        nullable=True,
    )

    error_code = Column(
        String(100),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    chunk = relationship(
        "DocumentChunk",
        back_populates="embeddings",
    )