"""Create persistent user sessions table.

Revision ID: 18b3c4d5e6f7
Revises: 18a2b3c4d5e6
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "18b3c4d5e6f7"
down_revision = "18a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "user_sessions",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "refresh_token_hash",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "current_refresh_jti",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "revoke_reason",
            sa.String(length=100),
            nullable=True,
        ),

        sa.PrimaryKeyConstraint(
            "id",
            name="pk_user_sessions",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_sessions_user_id_users",
            ondelete="CASCADE",
        ),

        sa.UniqueConstraint(
            "refresh_token_hash",
            name="uq_user_sessions_refresh_token_hash",
        ),
    )

    op.create_index(
        "ix_user_sessions_user_id",
        "user_sessions",
        ["user_id"],
    )

    op.create_index(
        "ix_user_sessions_expires_at",
        "user_sessions",
        ["expires_at"],
    )

    op.create_index(
        "ix_user_sessions_user_active",
        "user_sessions",
        ["user_id", "revoked_at", "expires_at"],
    )


def downgrade() -> None:

    op.drop_index(
        "ix_user_sessions_user_active",
        table_name="user_sessions",
    )

    op.drop_index(
        "ix_user_sessions_expires_at",
        table_name="user_sessions",
    )

    op.drop_index(
        "ix_user_sessions_user_id",
        table_name="user_sessions",
    )

    op.drop_table("user_sessions")
