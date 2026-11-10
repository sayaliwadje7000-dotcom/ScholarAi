"""
ScholarAI Role Model.

Phase 18.7: Database-backed Role-Based Access Control.
"""

import uuid

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Index,
    func,
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserRole(Base):

    __tablename__ = "user_roles"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "role",
            name="uq_user_roles_user_id_role",
        ),
        Index(
            "ix_user_roles_user_id",
            "user_id",
        ),
        Index(
            "ix_user_roles_role",
            "role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_user_roles_user_id_users",
        ),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self):
        return (
            f"<UserRole("
            f"user_id={self.user_id}, "
            f"role={self.role})>"
        )
