"""
Phase 18.2: Add password hash to users.

Revision ID: 18a2b3c4d5e6
Revises: 06011438fb1e
"""

from typing import Sequence, Union

from alembic import op

import sqlalchemy as sa


revision: str = "18a2b3c4d5e6"

down_revision: Union[
    str,
    Sequence[str],
    None
] = "06011438fb1e"

branch_labels = None

depends_on = None


def upgrade() -> None:
    """
    Add nullable password_hash to preserve existing users.
    """

    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """
    Remove password_hash.

    Downgrading will remove password credentials created
    after this migration.
    """

    op.drop_column(
        "users",
        "password_hash",
    )