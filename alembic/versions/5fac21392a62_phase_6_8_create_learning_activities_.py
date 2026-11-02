"""phase 6.8 create learning activities table

Revision ID: 5fac21392a62
Revises: 422f0b61a62b
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "5fac21392a62"
down_revision: Union[str, Sequence[str], None] = "422f0b61a62b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        "learning_activities",

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
            "activity_type",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "entity_type",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),

        sa.Column(
            "duration_seconds",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),

        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.CheckConstraint(
            "length(trim(activity_type)) > 0",
            name="ck_learning_activities_nonempty_activity_type",
        ),

        sa.CheckConstraint(
            "entity_type IS NULL OR length(trim(entity_type)) > 0",
            name="ck_learning_activities_valid_entity_type",
        ),

        sa.CheckConstraint(
            """
            (entity_type IS NULL AND entity_id IS NULL)
            OR
            (entity_type IS NOT NULL AND entity_id IS NOT NULL)
            """,
            name="ck_learning_activities_entity_reference_pair",
        ),

        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_learning_activities_nonnegative_duration",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_learning_activities_user_id_users",
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id",
            name="pk_learning_activities",
        ),
    )

    op.create_index(
        "ix_learning_activities_user_id",
        "learning_activities",
        ["user_id"],
    )

    op.create_index(
        "ix_learning_activities_occurred_at",
        "learning_activities",
        ["occurred_at"],
    )

    op.create_index(
        "ix_learning_activities_user_occurred",
        "learning_activities",
        ["user_id", "occurred_at"],
    )

    op.create_index(
        "ix_learning_activities_entity",
        "learning_activities",
        ["entity_type", "entity_id"],
    )


def downgrade() -> None:

    op.drop_index(
        "ix_learning_activities_entity",
        table_name="learning_activities",
    )

    op.drop_index(
        "ix_learning_activities_user_occurred",
        table_name="learning_activities",
    )

    op.drop_index(
        "ix_learning_activities_occurred_at",
        table_name="learning_activities",
    )

    op.drop_index(
        "ix_learning_activities_user_id",
        table_name="learning_activities",
    )

    op.drop_table("learning_activities")