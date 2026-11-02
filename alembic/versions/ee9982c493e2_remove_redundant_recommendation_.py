
"""remove redundant recommendation feedback index

Revision ID: ee9982c493e2
Revises: a9059d277400
Create Date: 2026-11-03 03:56:18.015341
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ee9982c493e2"
down_revision: Union[str, Sequence[str], None] = "a9059d277400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        "ix_recommendation_feedback_recommendation_id",
        table_name="recommendation_feedback",
    )


def downgrade() -> None:
    op.create_index(
        "ix_recommendation_feedback_recommendation_id",
        "recommendation_feedback",
        ["recommendation_id"],
        unique=False,
    )

