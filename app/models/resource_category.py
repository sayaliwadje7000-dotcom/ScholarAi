from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ResourceCategory(Base):
    __tablename__ = "resource_categories"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "resource_categories.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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

    parent: Mapped["ResourceCategory | None"] = relationship(
        "ResourceCategory",
        remote_side="ResourceCategory.id",
        back_populates="children",
    )

    children: Mapped[list["ResourceCategory"]] = relationship(
        "ResourceCategory",
        back_populates="parent",
    )

    study_resources = relationship(
        "StudyResource",
        secondary="study_resource_categories",
        back_populates="categories",
         passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="uq_resource_categories_name",
        ),
        UniqueConstraint(
            "slug",
            name="uq_resource_categories_slug",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_resource_categories_name_nonempty",
        ),
        CheckConstraint(
            "length(trim(slug)) > 0",
            name="ck_resource_categories_slug_nonempty",
        ),
        CheckConstraint(
            "slug = lower(slug)",
            name="ck_resource_categories_slug_lowercase",
        ),
        CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_resource_categories_no_self_parent",
        ),
        Index(
            "ix_resource_categories_parent_id",
            "parent_id",
        ),
        Index(
            "ix_resource_categories_is_active",
            "is_active",
        ),
        Index(
            "ix_resource_categories_name",
            "name",
        ),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid4())
        kwargs.setdefault("is_active", True)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<ResourceCategory("
            f"id={self.id}, "
            f"name={self.name!r}, "
            f"slug={self.slug!r})>"
        )