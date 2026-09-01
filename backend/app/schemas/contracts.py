from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RecurrenceType = Literal["daily", "weekdays", "weekends", "specific_days"]
DayPart = Literal["morning", "after_school", "evening"]
RewardStatus = Literal["pending", "approved", "rejected"]
SkipStatus = Literal["pending", "approved", "rejected"]


class ChoreWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    emoji: str = Field(default="✅", min_length=1, max_length=16)
    points: int = Field(default=0, ge=0, le=10_000)
    money_reward: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0"), max_digits=12, decimal_places=2
    )
    xoxo_reward: int = Field(default=0, ge=0, le=10_000)
    recurrence_type: RecurrenceType = "daily"
    recurrence_days: list[int] | None = None
    day_part: DayPart = "after_school"
    active: bool = True

    @field_validator("name", "emoji")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("recurrence_days")
    @classmethod
    def validate_days(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        days = sorted(set(value))
        if not days or any(day < 0 or day > 6 for day in days):
            raise ValueError("recurrence_days must contain weekday numbers from 0 through 6")
        return days

    @field_validator("money_reward")
    @classmethod
    def quantize_money_reward(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))

    @model_validator(mode="after")
    def validate_specific_days(self) -> "ChoreWrite":
        if self.points == 0 and self.money_reward == 0 and self.xoxo_reward == 0:
            raise ValueError("a chore must award points, money, or XOXOs")
        if self.recurrence_type == "specific_days" and not self.recurrence_days:
            raise ValueError("specific_days recurrence requires at least one recurrence day")
        if self.recurrence_type != "specific_days":
            self.recurrence_days = None
        return self


class ChoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    emoji: str
    points: int
    money_reward: Decimal
    xoxo_reward: int
    recurrence_type: RecurrenceType
    recurrence_days: list[int] | None
    day_part: DayPart
    active: bool
    completed: bool = False
    skip_status: SkipStatus | None = None


class RewardWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    emoji: str = Field(default="🎁", min_length=1, max_length=16)
    points_cost: int = Field(gt=0, le=1_000_000)
    active: bool = True

    @field_validator("name", "emoji")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return " ".join(value.split())


class RewardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    emoji: str
    points_cost: int
    active: bool


class RewardRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reward_id: UUID
    reward_name: str
    reward_emoji: str
    status: RewardStatus
    points_cost: int
    requested_at: datetime
    resolved_at: datetime | None


class ChoreSkipRequestRead(BaseModel):
    id: UUID
    chore_id: UUID
    chore_name: str
    chore_emoji: str
    skip_date: date
    status: SkipStatus
    requested_at: datetime
    resolved_at: datetime | None


class SavingsGoalWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    emoji: str = Field(default="🎯", min_length=1, max_length=16)
    target_amount: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=2)

    @field_validator("name", "emoji")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return " ".join(value.split())


class SavingsGoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    emoji: str
    target_amount: Decimal
    current_amount: Decimal
    progress_percent: int


class PointActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: int
    reason: str
    created_at: datetime


class KidDashboard(BaseModel):
    child_id: UUID
    child_name: str
    greeting: str
    date: date
    points_balance: int
    piggy_bank_balance: Decimal
    xoxo_balance: int
    piggy_bank_interest_rate: Decimal
    point_activity: list[PointActivityRead]
    chores: list[ChoreRead]
    completed_count: int
    total_count: int
    rewards: list[RewardRead]
    savings_goal: SavingsGoalRead | None
    streak_days: int
    pending_reward_count: int


class CompletionResult(BaseModel):
    chore_id: UUID
    points_awarded: int
    money_awarded: Decimal
    xoxos_awarded: int
    points_balance: int
    piggy_bank_balance: Decimal
    xoxo_balance: int
    message: str


class DayChoreRead(BaseModel):
    id: UUID
    name: str
    emoji: str
    day_part: DayPart
    completed: bool
    points_awarded: int
    money_awarded: Decimal
    xoxos_awarded: int
    skip_status: SkipStatus | None = None


class DailyRecord(BaseModel):
    date: date
    completed_count: int
    total_count: int
    chores: list[DayChoreRead]


class WeekDaySummary(BaseModel):
    date: date
    completed_count: int
    total_count: int
    future: bool = False


class WeekRecord(BaseModel):
    start_date: date
    end_date: date
    days: list[WeekDaySummary]


class HistoricalCompletionWrite(BaseModel):
    completed: bool
    reason: str = Field(min_length=1, max_length=240)

    @field_validator("reason")
    @classmethod
    def trim_historical_reason(cls, value: str) -> str:
        return " ".join(value.split())


class ChoreAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chore_id: UUID
    chore_name: str
    effective_date: date
    action: Literal["completed", "reopened"]
    actor: Literal["kid", "parent", "system"]
    points_delta: int
    money_delta: Decimal
    xoxos_delta: int
    reason: str
    created_at: datetime


class ParentDailyRecord(DailyRecord):
    audit: list[ChoreAuditRead]


class RewardRequestCreate(BaseModel):
    reward_id: UUID


class PinLogin(BaseModel):
    pin: str = Field(pattern=r"^\d{4}$")


class PinChange(BaseModel):
    current_pin: str = Field(pattern=r"^\d{4}$")
    new_pin: str = Field(pattern=r"^\d{4}$")

    @model_validator(mode="after")
    def require_new_pin(self) -> "PinChange":
        if self.current_pin == self.new_pin:
            raise ValueError("new PIN must be different")
        return self


class AdjustmentWrite(BaseModel):
    amount: int = Field(ge=-1_000_000, le=1_000_000)
    reason: str = Field(min_length=1, max_length=240)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("amount")
    @classmethod
    def non_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("amount must not be zero")
        return value


class MoneyAdjustmentWrite(BaseModel):
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    reason: str = Field(min_length=1, max_length=240)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("amount")
    @classmethod
    def non_zero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("amount must not be zero")
        return value.quantize(Decimal("0.01"))


class InterestRateWrite(BaseModel):
    annual_rate: Decimal = Field(ge=Decimal("0"), le=Decimal("100"), decimal_places=2)

    @field_validator("annual_rate")
    @classmethod
    def quantize_rate(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))


class InterestResult(BaseModel):
    annual_rate: Decimal
    interest_earned: Decimal
    balance: Decimal
    projected_one_year: Decimal


class WeatherRead(BaseModel):
    key: Literal["home", "school"]
    name: str
    location: str
    temperature: int
    high: int
    low: int
    weather_code: int
    label: str
    emoji: str


class BalanceResult(BaseModel):
    balance: int | Decimal


class PointTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: int
    reason: str
    source_type: str
    created_at: datetime


class PiggyTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    reason: str
    created_at: datetime


class XoxoTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: int
    reason: str
    created_at: datetime


class ParentOverview(BaseModel):
    dashboard: KidDashboard
    all_chores: list[ChoreRead]
    all_rewards: list[RewardRead]
    reward_requests: list[RewardRequestRead]
    skip_requests: list[ChoreSkipRequestRead]
    point_history: list[PointTransactionRead]
    piggy_bank_history: list[PiggyTransactionRead]
    xoxo_history: list[XoxoTransactionRead]


class RewardResolution(BaseModel):
    action: Literal["approve", "reject"]


class SkipResolution(BaseModel):
    action: Literal["approve", "reject"]
