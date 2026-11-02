
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class StudyResource(Base):
    __tablename__ = "study_resources"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Basic Resource Information
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    # Resource Provider Information
    provider: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    subject: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # Learning Information
    difficulty_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    estimated_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Resource Quality
    quality_score: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2),
        nullable=True,
    )

    # Flexible JSONB Metadata
    resource_metadata: Mapped[dict] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # Resource Availability
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Timestamps
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Phase 6.10: Many-to-Many Category Relationship
    categories: Mapped[list["ResourceCategory"]] = relationship(
        "ResourceCategory",
        secondary="study_resource_categories",
        back_populates="study_resources",
        passive_deletes=True,
    )

    # Phase 6.11: User Resource Interactions
    user_interactions: Mapped[
        list["UserResourceInteraction"]
    ] = relationship(
        "UserResourceInteraction",
        back_populates="resource",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="UserResourceInteraction.occurred_at",
    )

    # Database Constraints and Indexes
    __table_args__ = (
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_study_resources_title_nonempty",
        ),
        CheckConstraint(
            "length(trim(url)) > 0",
            name="ck_study_resources_url_nonempty",
        ),
        CheckConstraint(
            """
            resource_type IN (
                'video',
                'article',
                'notes',
                'course',
                'documentation',
                'tutorial',
                'website',
                'book'
            )
            """,
            name="ck_study_resources_valid_type",
        ),
        CheckConstraint(
            """
            difficulty_level IS NULL OR
            difficulty_level IN (
                'beginner',
                'intermediate',
                'advanced'
            )
            """,
            name="ck_study_resources_valid_difficulty",
        ),
        CheckConstraint(
            """
            estimated_duration_minutes IS NULL OR
            estimated_duration_minutes >= 0
            """,
            name="ck_study_resources_valid_duration",
        ),
        CheckConstraint(
            """
            quality_score IS NULL OR
            (quality_score >= 0 AND quality_score <= 5)
            """,
            name="ck_study_resources_valid_quality",
        ),
        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_study_resources_metadata_object",
        ),

        # Individual Indexes
        Index(
            "ix_study_resources_resource_type",
            "resource_type",
        ),
        Index(
            "ix_study_resources_subject",
            "subject",
        ),
        Index(
            "ix_study_resources_language",
            "language",
        ),
        Index(
            "ix_study_resources_difficulty",
            "difficulty_level",
        ),
        Index(
            "ix_study_resources_is_active",
            "is_active",
        ),
        Index(
            "ix_study_resources_quality_score",
            "quality_score",
        ),
        Index(
            "ix_study_resources_created_at",
            "created_at",
        ),

        # Composite Index
        Index(
            "ix_study_resources_subject_type_active",
            "subject",
            "resource_type",
            "is_active",
        ),
    )

    # Initialize Python-side defaults immediately
    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid4())
        kwargs.setdefault("resource_metadata", {})
        kwargs.setdefault("is_active", True)

        super().__init__(**kwargs)

    # String Representation
    def __repr__(self) -> str:
        return (
            f"<StudyResource("
            f"id={self.id}, "
            f"title={self.title!r}, "
            f"resource_type={self.resource_type!r})>"
        )

