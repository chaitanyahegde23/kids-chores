from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Child(TimestampMixin, Base):
    __tablename__ = "children"
    __table_args__ = (
        CheckConstraint("points_balance >= 0", name="points_balance_non_negative"),
        CheckConstraint("piggy_bank_balance >= 0", name="piggy_balance_non_negative"),
        CheckConstraint("xoxo_balance >= 0", name="xoxo_balance_non_negative"),
        CheckConstraint(
            "piggy_bank_interest_rate >= 0 AND piggy_bank_interest_rate <= 100",
            name="piggy_interest_rate_valid",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    points_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    piggy_bank_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    xoxo_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    piggy_bank_interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )

    chores: Mapped[list["Chore"]] = relationship(back_populates="child")
    rewards: Mapped[list["Reward"]] = relationship(back_populates="child")
    savings_goal: Mapped["SavingsGoal | None"] = relationship(back_populates="child")


class Chore(TimestampMixin, Base):
    __tablename__ = "chores"
    __table_args__ = (
        CheckConstraint("points >= 0", name="points_non_negative"),
        CheckConstraint("money_reward >= 0", name="money_reward_non_negative"),
        CheckConstraint("xoxo_reward >= 0", name="xoxo_reward_non_negative"),
        CheckConstraint(
            "points > 0 OR money_reward > 0 OR xoxo_reward > 0",
            name="reward_present",
        ),
        CheckConstraint(
            "recurrence_type IN ('daily', 'weekdays', 'weekends', 'specific_days')",
            name="recurrence_type_valid",
        ),
        CheckConstraint(
            "day_part IN ('morning', 'after_school', 'evening')",
            name="day_part_valid",
        ),
        Index("ix_chores_child_active", "child_id", "active"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="✅")
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    money_reward: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    xoxo_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recurrence_type: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    recurrence_days: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    day_part: Mapped[str] = mapped_column(String(20), nullable=False, default="after_school")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    child: Mapped[Child] = relationship(back_populates="chores")
    completions: Mapped[list["ChoreCompletion"]] = relationship(
        back_populates="chore", cascade="all, delete-orphan", passive_deletes=True
    )
    skip_requests: Mapped[list["ChoreSkipRequest"]] = relationship(
        back_populates="chore", cascade="all, delete-orphan", passive_deletes=True
    )


class ChoreCompletion(Base):
    __tablename__ = "chore_completions"
    __table_args__ = (
        UniqueConstraint("chore_id", "child_id", "completion_date"),
        CheckConstraint("points_awarded >= 0", name="points_awarded_non_negative"),
        CheckConstraint("money_awarded >= 0", name="money_awarded_non_negative"),
        CheckConstraint("xoxos_awarded >= 0", name="xoxos_awarded_non_negative"),
        CheckConstraint(
            "points_awarded > 0 OR money_awarded > 0 OR xoxos_awarded > 0",
            name="award_present",
        ),
        Index("ix_chore_completions_child_date", "child_id", "completion_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    chore_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("chores.id", ondelete="CASCADE"), nullable=False
    )
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    completion_date: Mapped[date] = mapped_column(Date, nullable=False)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    money_awarded: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    xoxos_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    chore: Mapped[Chore] = relationship(back_populates="completions")


class ChoreSkipRequest(Base):
    __tablename__ = "chore_skip_requests"
    __table_args__ = (
        UniqueConstraint(
            "chore_id", "child_id", "skip_date", name="uq_chore_skip_requests_chore_child_date"
        ),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="status_valid"),
        Index("ix_chore_skip_requests_child_status", "child_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    chore_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("chores.id", ondelete="CASCADE"), nullable=False
    )
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    skip_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chore: Mapped[Chore] = relationship(back_populates="skip_requests")


class ChoreAuditEvent(Base):
    __tablename__ = "chore_audit_events"
    __table_args__ = (
        CheckConstraint("action IN ('completed', 'reopened')", name="action_valid"),
        CheckConstraint("actor IN ('kid', 'parent', 'system')", name="actor_valid"),
        CheckConstraint(
            "points_delta <> 0 OR money_delta <> 0 OR xoxos_delta <> 0",
            name="reward_delta_present",
        ),
        Index("ix_chore_audit_child_date", "child_id", "effective_date", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    chore_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    chore_name: Mapped[str] = mapped_column(String(120), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor: Mapped[str] = mapped_column(String(20), nullable=False)
    points_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    money_delta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    xoxos_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(String(240), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PointTransaction(Base):
    __tablename__ = "point_transactions"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="amount_non_zero"),
        Index("ix_point_transactions_child_created", "child_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PiggyBankTransaction(Base):
    __tablename__ = "piggy_bank_transactions"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="amount_non_zero"),
        Index("ix_piggy_transactions_child_created", "child_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(240), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class XoxoTransaction(Base):
    __tablename__ = "xoxo_transactions"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="amount_non_zero"),
        Index("ix_xoxo_transactions_child_created", "child_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(240), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class HouseholdSecurity(TimestampMixin, Base):
    __tablename__ = "household_security"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    pin_salt: Mapped[str] = mapped_column(String(64), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(128), nullable=False)


class Reward(TimestampMixin, Base):
    __tablename__ = "rewards"
    __table_args__ = (
        CheckConstraint("points_cost > 0", name="points_cost_positive"),
        Index("ix_rewards_child_active", "child_id", "active"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="🎁")
    points_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    child: Mapped[Child] = relationship(back_populates="rewards")
    requests: Mapped[list["RewardRequest"]] = relationship(
        back_populates="reward", cascade="all, delete-orphan", passive_deletes=True
    )


class RewardRequest(Base):
    __tablename__ = "reward_requests"
    __table_args__ = (
        CheckConstraint("points_cost > 0", name="points_cost_positive"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="status_valid"),
        Index("ix_reward_requests_child_status", "child_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reward_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("rewards.id", ondelete="CASCADE"), nullable=False
    )
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    points_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reward: Mapped[Reward] = relationship(back_populates="requests")


class SavingsGoal(TimestampMixin, Base):
    __tablename__ = "savings_goals"
    __table_args__ = (CheckConstraint("target_amount > 0", name="target_amount_positive"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    child_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("children.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="🎯")
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    child: Mapped[Child] = relationship(back_populates="savings_goal")
