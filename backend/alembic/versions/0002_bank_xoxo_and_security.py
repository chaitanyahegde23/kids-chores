"""Add bank settings, XOXOs, and PIN override storage.

Revision ID: 0002_bank_xoxo_security
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_bank_xoxo_security"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "children", sa.Column("xoxo_balance", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "children",
        sa.Column(
            "piggy_bank_interest_rate",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0.00",
        ),
    )
    op.create_check_constraint("xoxo_balance_non_negative", "children", "xoxo_balance >= 0")
    op.create_check_constraint(
        "piggy_interest_rate_valid",
        "children",
        "piggy_bank_interest_rate >= 0 AND piggy_bank_interest_rate <= 100",
    )
    op.create_table(
        "xoxo_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=240), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount <> 0", name=op.f("ck_xoxo_transactions_amount_non_zero")),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name=op.f("fk_xoxo_transactions_child_id_children"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_xoxo_transactions")),
    )
    op.create_index(
        "ix_xoxo_transactions_child_created",
        "xoxo_transactions",
        ["child_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "household_security",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pin_salt", sa.String(length=64), nullable=False),
        sa.Column("pin_hash", sa.String(length=128), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_household_security")),
    )


def downgrade() -> None:
    op.drop_table("household_security")
    op.drop_index("ix_xoxo_transactions_child_created", table_name="xoxo_transactions")
    op.drop_table("xoxo_transactions")
    op.drop_constraint("ck_children_piggy_interest_rate_valid", "children", type_="check")
    op.drop_constraint("ck_children_xoxo_balance_non_negative", "children", type_="check")
    op.drop_column("children", "piggy_bank_interest_rate")
    op.drop_column("children", "xoxo_balance")
