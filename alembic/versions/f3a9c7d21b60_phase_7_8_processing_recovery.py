"""Phase 7.8 - processing status and failure recovery.

Revision ID: f3a9c7d21b60
Revises: ee9982c493e2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a9c7d21b60"

down_revision: Union[str, Sequence[str], None] = "ee9982c493e2"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(
        "documents",
        sa.Column(
            "processing_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "processing_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "processing_error",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "processing_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    op.create_check_constraint(
        "ck_documents_nonnegative_processing_attempts",
        "documents",
        "processing_attempts >= 0",
    )


def downgrade() -> None:

    op.drop_constraint(
        "ck_documents_nonnegative_processing_attempts",
        "documents",
        type_="check",
    )

    op.drop_column(
        "documents",
        "processing_attempts",
    )

    op.drop_column(
        "documents",
        "processing_error",
    )

    op.drop_column(
        "documents",
        "processing_completed_at",
    )

    op.drop_column(
        "documents",
        "processing_started_at",
    )