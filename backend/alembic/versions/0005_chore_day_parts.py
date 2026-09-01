"""Add chore day-part grouping.

Revision ID: 0005_chore_day_parts
Revises: 0004_chore_history
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_chore_day_parts"
down_revision: str | None = "0004_chore_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chores",
        sa.Column(
            "day_part",
            sa.String(length=20),
            nullable=False,
            server_default="after_school",
        ),
    )
    op.create_check_constraint(
        op.f("ck_chores_day_part_valid"),
        "chores",
        "day_part IN ('morning', 'after_school', 'evening')",
    )
    op.execute(
        """
        UPDATE chores
        SET day_part = 'morning'
        WHERE lower(name) LIKE '%morning%'
           OR lower(name) LIKE '%make bed%'
           OR lower(name) LIKE '%brush teeth%'
        """
    )
    op.execute(
        """
        UPDATE chores
        SET day_part = 'evening'
        WHERE lower(name) LIKE '%evening%'
           OR lower(name) LIKE '%bedtime%'
           OR lower(name) LIKE '%dinner%'
        """
    )
    op.alter_column("chores", "day_part", server_default=None)


def downgrade() -> None:
    op.drop_constraint(op.f("ck_chores_day_part_valid"), "chores", type_="check")
    op.drop_column("chores", "day_part")
