"""add chore skip requests

Revision ID: 0006_chore_skip_requests
Revises: 0005_chore_day_parts
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_chore_skip_requests"
down_revision: str | None = "0005_chore_day_parts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chore_skip_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chore_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("skip_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name=op.f("ck_chore_skip_requests_status_valid"),
        ),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chore_id"], ["chores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chore_id",
            "child_id",
            "skip_date",
            name="uq_chore_skip_requests_chore_child_date",
        ),
    )
    op.create_index(
        "ix_chore_skip_requests_child_status",
        "chore_skip_requests",
        ["child_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_chore_skip_requests_child_status", table_name="chore_skip_requests")
    op.drop_table("chore_skip_requests")
