from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import relationship

from pgvector.sqlalchemy import VECTOR

from app.database.base import Base


VECTOR_DIMENSIONS = 1536

RESOURCE_EMBEDDING_PIPELINE_VERSION = "1.0.0"


class ResourceEmbedding(Base):
    """
    Stores versioned semantic embeddings for study resources.

    Resource embeddings are independent of document chunk
    embeddings used by the RAG pipeline.
    """

    __tablename__ = "resource_embeddings"

    __table_args__ = (
        UniqueConstraint(
            "resource_id",
            "content_hash",
            "provider",
            "model",
            "model_version",
            "dimensions",
            "pipeline_version",
            name="uq_resource_embeddings_identity",
        ),

        CheckConstraint(
            "dimensions > 0",
            name="ck_resource_embeddings_dimensions_positive",
        ),

        CheckConstraint(
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

        CheckConstraint(
            """
            embedding IS NULL OR dimensions = 1536
            """,
            name="ck_resource_embeddings_vector_dimensions",
        ),

        Index(
            "ix_resource_embeddings_resource_id",
            "resource_id",
        ),

        Index(
            "ix_resource_embeddings_status",
            "status",
        ),

        Index(
            "ix_resource_embeddings_model_dimensions",
            "model",
            "dimensions",
        ),

        Index(
            "ix_resource_embeddings_embedding_hnsw",
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

    resource_id = Column(
        __import__("sqlalchemy").Uuid(as_uuid=True),
        ForeignKey(
            "study_resources.id",
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
    )

    dimensions = Column(
        Integer,
        nullable=False,
    )

    pipeline_version = Column(
        String(50),
        nullable=False,
        default=RESOURCE_EMBEDDING_PIPELINE_VERSION,
    )

    status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

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

    resource = relationship(
        "StudyResource",
    )

    def __repr__(self) -> str:
        return (
            f"<ResourceEmbedding("
            f"id={self.id}, "
            f"resource_id={self.resource_id}, "
            f"status={self.status!r})>"
        )