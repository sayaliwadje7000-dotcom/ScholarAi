"""phase 13.4 create opportunities table

Revision ID: 06011438fb1e
Revises: c8d4e7a91f20
Create Date: 2026-11-08 02:17:35.490628

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Revision identifiers used by Alembic.
revision: str = "06011438fb1e"
down_revision: Union[str, Sequence[str], None] = "c8d4e7a91f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the opportunities table."""

    op.create_table(
        "opportunities",

        sa.Column("id", sa.UUID(), nullable=False),

        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=500), nullable=True),

        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),

        sa.Column("opportunity_type", sa.String(length=50), nullable=False),
        sa.Column("organizer", sa.String(length=255), nullable=True),

        sa.Column("official_url", sa.String(length=2048), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("application_url", sa.String(length=2048), nullable=True),

        sa.Column(
            "eligibility",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),

        sa.Column(
            "required_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),

        sa.Column("location", sa.String(length=255), nullable=True),

        sa.Column(
            "is_remote",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),

        sa.Column(
            "registration_start",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "registration_deadline",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "event_start",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "event_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),

        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "retrieved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),

        sa.Column(
            "retrieval_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        # Opportunity type validation.
        sa.CheckConstraint(
            """
            opportunity_type IN (
                'hackathon',
                'internship',
                'competition',
                'workshop',
                'conference',
                'academic_event',
                'scholarship',
                'other'
            )
            """,
            name="ck_opportunities_valid_type",
        ),

        # Opportunity status validation.
        sa.CheckConstraint(
            """
            status IN (
                'unknown',
                'upcoming',
                'open',
                'closed',
                'expired',
                'cancelled'
            )
            """,
            name="ck_opportunities_valid_status",
        ),

        # JSONB validation.
        sa.CheckConstraint(
            "jsonb_typeof(eligibility) = 'object'",
            name="ck_opportunities_eligibility_object",
        ),

        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_opportunities_metadata_object",
        ),

        sa.CheckConstraint(
            "jsonb_typeof(required_skills) = 'array'",
            name="ck_opportunities_required_skills_array",
        ),

        # Event date validation.
        sa.CheckConstraint(
            """
            event_start IS NULL
            OR event_end IS NULL
            OR event_start <= event_end
            """,
            name="ck_opportunities_valid_event_dates",
        ),

        # Registration date validation.
        sa.CheckConstraint(
            """
            registration_start IS NULL
            OR registration_deadline IS NULL
            OR registration_start <= registration_deadline
            """,
            name="ck_opportunities_valid_registration_dates",
        ),

        # Retrieval count validation.
        sa.CheckConstraint(
            "retrieval_count >= 0",
            name="ck_opportunities_nonnegative_retrieval_count",
        ),

        # Required string validation.
        sa.CheckConstraint(
            "length(trim(provider)) > 0",
            name="ck_opportunities_provider_nonempty",
        ),

        sa.CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_opportunities_title_nonempty",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "provider",
            "external_id",
            name="uq_opportunities_provider_external_id",
        ),
    )

    # Indexes for discovery, filtering and ranking.
    op.create_index(
        "ix_opportunities_event_start",
        "opportunities",
        ["event_start"],
        unique=False,
    )

    op.create_index(
        "ix_opportunities_is_active",
        "opportunities",
        ["is_active"],
        unique=False,
    )

    op.create_index(
        "ix_opportunities_opportunity_type",
        "opportunities",
        ["opportunity_type"],
        unique=False,
    )

    op.create_index(
        "ix_opportunities_provider",
        "opportunities",
        ["provider"],
        unique=False,
    )

    op.create_index(
        "ix_opportunities_registration_deadline",
        "opportunities",
        ["registration_deadline"],
        unique=False,
    )

    op.create_index(
        "ix_opportunities_retrieved_at",
        "opportunities",
        ["retrieved_at"],
        unique=False,
    )

    op.create_index(
        "ix_opportunities_status",
        "opportunities",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_opportunities_type_status_active",
        "opportunities",
        ["opportunity_type", "status", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the opportunities table and its indexes."""

    op.drop_index(
        "ix_opportunities_type_status_active",
        table_name="opportunities",
    )

    op.drop_index(
        "ix_opportunities_status",
        table_name="opportunities",
    )

    op.drop_index(
        "ix_opportunities_retrieved_at",
        table_name="opportunities",
    )

    op.drop_index(
        "ix_opportunities_registration_deadline",
        table_name="opportunities",
    )

    op.drop_index(
        "ix_opportunities_provider",
        table_name="opportunities",
    )

    op.drop_index(
        "ix_opportunities_opportunity_type",
        table_name="opportunities",
    )

    op.drop_index(
        "ix_opportunities_is_active",
        table_name="opportunities",
    )

    op.drop_index(
        "ix_opportunities_event_start",
        table_name="opportunities",
    )

    op.drop_table("opportunities")