"""Add immutable chore history audit events.

Revision ID: 0004_chore_history
Revises: 0003_chore_rewards
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_chore_history"
down_revision: str | None = "0003_chore_rewards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chore_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("chore_id", sa.Uuid(), nullable=False),
        sa.Column("chore_name", sa.String(length=120), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("points_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "money_delta",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("xoxos_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=240), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('completed', 'reopened')",
            name=op.f("ck_chore_audit_events_action_valid"),
        ),
        sa.CheckConstraint(
            "actor IN ('kid', 'parent', 'system')",
            name=op.f("ck_chore_audit_events_actor_valid"),
        ),
        sa.CheckConstraint(
            "points_delta <> 0 OR money_delta <> 0 OR xoxos_delta <> 0",
            name=op.f("ck_chore_audit_events_reward_delta_present"),
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name=op.f("fk_chore_audit_events_child_id_children"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chore_audit_events")),
    )
    op.create_index(
        "ix_chore_audit_child_date",
        "chore_audit_events",
        ["child_id", "effective_date", "created_at"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO chore_audit_events (
            id, child_id, chore_id, chore_name, effective_date, action, actor,
            points_delta, money_delta, xoxos_delta, reason, created_at
        )
        SELECT
            gen_random_uuid(), cc.child_id, cc.chore_id, c.name, cc.completion_date,
            'completed', 'system', cc.points_awarded, cc.money_awarded,
            cc.xoxos_awarded, 'Imported existing completion', cc.created_at
        FROM chore_completions AS cc
        JOIN chores AS c ON c.id = cc.chore_id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_chore_audit_child_date", table_name="chore_audit_events")
    op.drop_table("chore_audit_events")
