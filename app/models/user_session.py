"""
ScholarAI persistent user authentication sessions.
"""

import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserSession(Base):

    __tablename__ = "user_sessions"

    __table_args__ = (
        UniqueConstraint(
            "refresh_token_hash",
            name="uq_user_sessions_refresh_token_hash",
        ),
        Index(
            "ix_user_sessions_user_id",
            "user_id",
        ),
        Index(
            "ix_user_sessions_expires_at",
            "expires_at",
        ),
        Index(
            "ix_user_sessions_user_active",
            "user_id",
            "revoked_at",
            "expires_at",
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
            name="fk_user_sessions_user_id_users",
        ),
        nullable=False,
    )

    refresh_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    current_refresh_jti: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoke_reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<UserSession(id={self.id}, "
            f"user_id={self.user_id}, "
            f"expires_at={self.expires_at}, "
            f"revoked_at={self.revoked_at})>"
        )
