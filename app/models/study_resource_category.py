from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Table,
    func,
)

from app.database.base import Base


study_resource_categories = Table(
    "study_resource_categories",
    Base.metadata,

    Column(
        "resource_id",
        ForeignKey(
            "study_resources.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),

    Column(
        "category_id",
        ForeignKey(
            "resource_categories.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),

    Column(
        "assigned_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),

    Index(
        "ix_study_resource_categories_category_id",
        "category_id",
    ),
)