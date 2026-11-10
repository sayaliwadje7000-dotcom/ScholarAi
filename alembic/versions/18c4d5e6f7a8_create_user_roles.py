"""Create user roles table.

Revision ID: 18c4d5e6f7a8
Revises: 18b3c4d5e6f7
"""

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql


revision = "18c4d5e6f7a8"

down_revision = "18b3c4d5e6f7"

branch_labels = None

depends_on = None


def upgrade() -> None:

    op.create_table(
        "user_roles",

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
            "role",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint(
            "id",
            name="pk_user_roles",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_roles_user_id_users",
            ondelete="CASCADE",
        ),

        sa.UniqueConstraint(
            "user_id",
            "role",
            name="uq_user_roles_user_id_role",
        ),
    )

    op.create_index(
        "ix_user_roles_user_id",
        "user_roles",
        ["user_id"],
    )

    op.create_index(
        "ix_user_roles_role",
        "user_roles",
        ["role"],
    )


def downgrade() -> None:

    op.drop_index(
        "ix_user_roles_role",
        table_name="user_roles",
    )

    op.drop_index(
        "ix_user_roles_user_id",
        table_name="user_roles",
    )

    op.drop_table("user_roles")
