
"""phase 6.11 create user resource interactions

Revision ID: de57b9b0ebdf
Revises: 6310f4ccad95
Create Date: 2026-11-02 08:53:20.078941

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "de57b9b0ebdf"
down_revision: Union[str, Sequence[str], None] = "6310f4ccad95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "user_resource_interactions",

        # Primary Key
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        # Foreign Keys
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "resource_id",
            sa.UUID(),
            nullable=False,
        ),

        # Interaction Information
        sa.Column(
            "interaction_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "rating",
            sa.SmallInteger(),
            nullable=True,
        ),
        sa.Column(
            "duration_seconds",
            sa.Integer(),
            nullable=True,
        ),

        # JSONB Metadata
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),

        # Timestamp
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        # Check Constraints
        sa.CheckConstraint(
            """
            (
                interaction_type = 'rate'
                AND rating IS NOT NULL
                AND rating BETWEEN 1 AND 5
            )
            OR
            (
                interaction_type <> 'rate'
                AND rating IS NULL
            )
            """,
            name="ck_user_resource_interactions_valid_rating",
        ),

        sa.CheckConstraint(
            """
            interaction_type IN (
                'view',
                'click',
                'save',
                'rate',
                'complete'
            )
            """,
            name="ck_user_resource_interactions_valid_type",
        ),

        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_user_resource_interactions_metadata_object",
        ),

        sa.CheckConstraint(
            """
            duration_seconds IS NULL
            OR duration_seconds >= 0
            """,
            name="ck_user_resource_interactions_valid_duration",
        ),

        # Foreign Key Constraints
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["study_resources.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        # Primary Key Constraint
        sa.PrimaryKeyConstraint("id"),
    )

    # Individual Indexes
    op.create_index(
        "ix_user_resource_interactions_interaction_type",
        "user_resource_interactions",
        ["interaction_type"],
        unique=False,
    )

    op.create_index(
        "ix_user_resource_interactions_occurred_at",
        "user_resource_interactions",
        ["occurred_at"],
        unique=False,
    )

    op.create_index(
        "ix_user_resource_interactions_resource_id",
        "user_resource_interactions",
        ["resource_id"],
        unique=False,
    )

    op.create_index(
        "ix_user_resource_interactions_user_id",
        "user_resource_interactions",
        ["user_id"],
        unique=False,
    )

    # Composite Indexes
    op.create_index(
        "ix_user_resource_interactions_user_occurred",
        "user_resource_interactions",
        ["user_id", "occurred_at"],
        unique=False,
    )

    op.create_index(
        "ix_user_resource_interactions_user_resource",
        "user_resource_interactions",
        ["user_id", "resource_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_user_resource_interactions_user_resource",
        table_name="user_resource_interactions",
    )

    op.drop_index(
        "ix_user_resource_interactions_user_occurred",
        table_name="user_resource_interactions",
    )

    op.drop_index(
        "ix_user_resource_interactions_user_id",
        table_name="user_resource_interactions",
    )

    op.drop_index(
        "ix_user_resource_interactions_resource_id",
        table_name="user_resource_interactions",
    )

    op.drop_index(
        "ix_user_resource_interactions_occurred_at",
        table_name="user_resource_interactions",
    )

    op.drop_index(
        "ix_user_resource_interactions_interaction_type",
        table_name="user_resource_interactions",
    )

    op.drop_table("user_resource_interactions")

