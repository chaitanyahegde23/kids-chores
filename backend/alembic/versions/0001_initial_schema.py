"""Create chores, rewards, ledgers, and savings schema.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "children",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("points_balance", sa.Integer(), nullable=False),
        sa.Column("piggy_bank_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "piggy_bank_balance >= 0", name="ck_children_piggy_balance_non_negative"
        ),
        sa.CheckConstraint("points_balance >= 0", name="ck_children_points_balance_non_negative"),
        sa.PrimaryKeyConstraint("id", name="pk_children"),
    )
    op.create_table(
        "chores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("recurrence_type", sa.String(length=20), nullable=False),
        sa.Column("recurrence_days", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("points > 0", name="ck_chores_points_positive"),
        sa.CheckConstraint(
            "recurrence_type IN ('daily', 'weekdays', 'weekends', 'specific_days')",
            name="ck_chores_recurrence_type_valid",
        ),
        sa.ForeignKeyConstraint(
            ["child_id"], ["children.id"], name="fk_chores_child_id_children", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chores"),
    )
    op.create_index("ix_chores_child_active", "chores", ["child_id", "active"])
    op.create_table(
        "rewards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=False),
        sa.Column("points_cost", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("points_cost > 0", name="ck_rewards_points_cost_positive"),
        sa.ForeignKeyConstraint(
            ["child_id"], ["children.id"], name="fk_rewards_child_id_children", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rewards"),
    )
    op.create_index("ix_rewards_child_active", "rewards", ["child_id", "active"])
    op.create_table(
        "savings_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=False),
        sa.Column("target_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("target_amount > 0", name="ck_savings_goals_target_amount_positive"),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="fk_savings_goals_child_id_children",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_savings_goals"),
        sa.UniqueConstraint("child_id", name="uq_savings_goals_child_id"),
    )
    op.create_table(
        "chore_completions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chore_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "points_awarded > 0", name="ck_chore_completions_points_awarded_positive"
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="fk_chore_completions_child_id_children",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chore_id"],
            ["chores.id"],
            name="fk_chore_completions_chore_id_chores",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chore_completions"),
        sa.UniqueConstraint(
            "chore_id",
            "child_id",
            "completion_date",
            name="uq_chore_completions_chore_id",
        ),
    )
    op.create_index(
        "ix_chore_completions_child_date",
        "chore_completions",
        ["child_id", "completion_date"],
    )
    op.create_table(
        "point_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=240), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount <> 0", name="ck_point_transactions_amount_non_zero"),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="fk_point_transactions_child_id_children",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_point_transactions"),
    )
    op.create_index(
        "ix_point_transactions_child_created",
        "point_transactions",
        ["child_id", "created_at"],
    )
    op.create_table(
        "piggy_bank_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.String(length=240), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount <> 0", name="ck_piggy_bank_transactions_amount_non_zero"),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="fk_piggy_bank_transactions_child_id_children",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_piggy_bank_transactions"),
    )
    op.create_index(
        "ix_piggy_transactions_child_created",
        "piggy_bank_transactions",
        ["child_id", "created_at"],
    )
    op.create_table(
        "reward_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reward_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("points_cost", sa.Integer(), nullable=False),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("points_cost > 0", name="ck_reward_requests_points_cost_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_reward_requests_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="fk_reward_requests_child_id_children",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reward_id"],
            ["rewards.id"],
            name="fk_reward_requests_reward_id_rewards",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reward_requests"),
    )
    op.create_index("ix_reward_requests_child_status", "reward_requests", ["child_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_reward_requests_child_status", table_name="reward_requests")
    op.drop_table("reward_requests")
    op.drop_index("ix_piggy_transactions_child_created", table_name="piggy_bank_transactions")
    op.drop_table("piggy_bank_transactions")
    op.drop_index("ix_point_transactions_child_created", table_name="point_transactions")
    op.drop_table("point_transactions")
    op.drop_index("ix_chore_completions_child_date", table_name="chore_completions")
    op.drop_table("chore_completions")
    op.drop_table("savings_goals")
    op.drop_index("ix_rewards_child_active", table_name="rewards")
    op.drop_table("rewards")
    op.drop_index("ix_chores_child_active", table_name="chores")
    op.drop_table("chores")
    op.drop_table("children")
