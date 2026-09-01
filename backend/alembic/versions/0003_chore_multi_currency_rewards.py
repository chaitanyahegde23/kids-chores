"""Add multi-currency chore rewards.

Revision ID: 0003_chore_rewards
Revises: 0002_bank_xoxo_security
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_chore_rewards"
down_revision: str | None = "0002_bank_xoxo_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chores",
        sa.Column(
            "money_reward",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0.00",
        ),
    )
    op.add_column(
        "chores", sa.Column("xoxo_reward", sa.Integer(), nullable=False, server_default="0")
    )
    op.drop_constraint("ck_chores_points_positive", "chores", type_="check")
    op.create_check_constraint("points_non_negative", "chores", "points >= 0")
    op.create_check_constraint("money_reward_non_negative", "chores", "money_reward >= 0")
    op.create_check_constraint("xoxo_reward_non_negative", "chores", "xoxo_reward >= 0")
    op.create_check_constraint(
        "reward_present", "chores", "points > 0 OR money_reward > 0 OR xoxo_reward > 0"
    )

    op.add_column(
        "chore_completions",
        sa.Column(
            "money_awarded",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0.00",
        ),
    )
    op.add_column(
        "chore_completions",
        sa.Column("xoxos_awarded", sa.Integer(), nullable=False, server_default="0"),
    )
    op.drop_constraint(
        "ck_chore_completions_points_awarded_positive", "chore_completions", type_="check"
    )
    op.create_check_constraint(
        "points_awarded_non_negative", "chore_completions", "points_awarded >= 0"
    )
    op.create_check_constraint(
        "money_awarded_non_negative", "chore_completions", "money_awarded >= 0"
    )
    op.create_check_constraint(
        "xoxos_awarded_non_negative", "chore_completions", "xoxos_awarded >= 0"
    )
    op.create_check_constraint(
        "award_present",
        "chore_completions",
        "points_awarded > 0 OR money_awarded > 0 OR xoxos_awarded > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_chore_completions_award_present", "chore_completions", type_="check")
    op.drop_constraint(
        "ck_chore_completions_xoxos_awarded_non_negative", "chore_completions", type_="check"
    )
    op.drop_constraint(
        "ck_chore_completions_money_awarded_non_negative", "chore_completions", type_="check"
    )
    op.drop_constraint(
        "ck_chore_completions_points_awarded_non_negative", "chore_completions", type_="check"
    )
    op.execute("UPDATE chore_completions SET points_awarded = 1 WHERE points_awarded = 0")
    op.create_check_constraint("points_awarded_positive", "chore_completions", "points_awarded > 0")
    op.drop_column("chore_completions", "xoxos_awarded")
    op.drop_column("chore_completions", "money_awarded")

    op.drop_constraint("ck_chores_reward_present", "chores", type_="check")
    op.drop_constraint("ck_chores_xoxo_reward_non_negative", "chores", type_="check")
    op.drop_constraint("ck_chores_money_reward_non_negative", "chores", type_="check")
    op.drop_constraint("ck_chores_points_non_negative", "chores", type_="check")
    op.execute("UPDATE chores SET points = 1 WHERE points = 0")
    op.create_check_constraint("points_positive", "chores", "points > 0")
    op.drop_column("chores", "xoxo_reward")
    op.drop_column("chores", "money_reward")
