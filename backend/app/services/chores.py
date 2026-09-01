from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal, cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Child,
    Chore,
    ChoreAuditEvent,
    ChoreCompletion,
    ChoreSkipRequest,
    PiggyBankTransaction,
    PointTransaction,
    Reward,
    RewardRequest,
    SavingsGoal,
    XoxoTransaction,
)
from app.schemas.contracts import (
    ChoreAuditRead,
    ChoreRead,
    ChoreSkipRequestRead,
    DailyRecord,
    DayChoreRead,
    DayPart,
    KidDashboard,
    ParentDailyRecord,
    ParentOverview,
    PiggyTransactionRead,
    PointActivityRead,
    PointTransactionRead,
    RewardRead,
    RewardRequestRead,
    SavingsGoalRead,
    SkipStatus,
    WeekDaySummary,
    WeekRecord,
    XoxoTransactionRead,
)


def household_today(timezone_name: str) -> date:
    return datetime.now(ZoneInfo(timezone_name)).date()


def first_child(session: Session, *, lock: bool = False) -> Child:
    statement = select(Child).order_by(Child.created_at, Child.id).limit(1)
    if lock:
        statement = statement.with_for_update()
    child = session.scalar(statement)
    if child is None:
        raise HTTPException(status_code=404, detail="No child has been configured")
    return child


def chore_occurs_on(chore: Chore, day: date) -> bool:
    if not chore.active:
        return False
    weekday = day.weekday()
    if chore.recurrence_type == "daily":
        return True
    if chore.recurrence_type == "weekdays":
        return weekday < 5
    if chore.recurrence_type == "weekends":
        return weekday >= 5
    return weekday in (chore.recurrence_days or [])


def calculate_streak(
    chores: list[Chore],
    completions: set[tuple[UUID, date]],
    approved_skips: set[tuple[UUID, date]],
    today: date,
) -> int:
    streak = 0
    cursor = today
    for _ in range(366):
        due = [
            chore
            for chore in chores
            if chore_occurs_on(chore, cursor) and (chore.id, cursor) not in approved_skips
        ]
        if not due:
            cursor -= timedelta(days=1)
            continue
        all_done = all((chore.id, cursor) in completions for chore in due)
        if all_done:
            streak += 1
            cursor -= timedelta(days=1)
            continue
        if cursor == today:
            cursor -= timedelta(days=1)
            continue
        break
    return streak


def _reward_request_read(request: RewardRequest) -> RewardRequestRead:
    return RewardRequestRead(
        id=request.id,
        reward_id=request.reward_id,
        reward_name=request.reward.name,
        reward_emoji=request.reward.emoji,
        status=request.status,  # type: ignore[arg-type]
        points_cost=request.points_cost,
        requested_at=request.requested_at,
        resolved_at=request.resolved_at,
    )


def _skip_request_read(request: ChoreSkipRequest) -> ChoreSkipRequestRead:
    return ChoreSkipRequestRead(
        id=request.id,
        chore_id=request.chore_id,
        chore_name=request.chore.name,
        chore_emoji=request.chore.emoji,
        skip_date=request.skip_date,
        status=cast(SkipStatus, request.status),
        requested_at=request.requested_at,
        resolved_at=request.resolved_at,
    )


def build_dashboard(session: Session, timezone_name: str) -> KidDashboard:
    child = first_child(session)
    today = household_today(timezone_name)
    chores = list(
        session.scalars(
            select(Chore).where(Chore.child_id == child.id).order_by(Chore.created_at, Chore.id)
        )
    )
    due = [chore for chore in chores if chore_occurs_on(chore, today)]
    recent_start = today - timedelta(days=366)
    completion_rows = session.execute(
        select(ChoreCompletion.chore_id, ChoreCompletion.completion_date).where(
            ChoreCompletion.child_id == child.id,
            ChoreCompletion.completion_date >= recent_start,
            ChoreCompletion.completion_date <= today,
        )
    ).all()
    completed = {(row.chore_id, row.completion_date) for row in completion_rows}
    skip_rows = list(
        session.scalars(
            select(ChoreSkipRequest).where(
                ChoreSkipRequest.child_id == child.id,
                ChoreSkipRequest.skip_date >= recent_start,
                ChoreSkipRequest.skip_date <= today,
            )
        )
    )
    approved_skips = {
        (request.chore_id, request.skip_date)
        for request in skip_rows
        if request.status == "approved"
    }
    today_skip_by_chore = {
        request.chore_id: request for request in skip_rows if request.skip_date == today
    }
    required_due = [chore for chore in due if (chore.id, today) not in approved_skips]
    rewards = list(
        session.scalars(
            select(Reward)
            .where(Reward.child_id == child.id, Reward.active.is_(True))
            .order_by(Reward.points_cost, Reward.id)
        )
    )
    goal = session.scalar(select(SavingsGoal).where(SavingsGoal.child_id == child.id))
    pending_count = len(
        list(
            session.scalars(
                select(RewardRequest.id).where(
                    RewardRequest.child_id == child.id, RewardRequest.status == "pending"
                )
            )
        )
    )
    point_activity = list(
        session.scalars(
            select(PointTransaction)
            .where(PointTransaction.child_id == child.id)
            .order_by(PointTransaction.created_at.desc(), PointTransaction.id.desc())
            .limit(8)
        )
    )
    goal_read = None
    if goal is not None:
        percent = min(
            100,
            int(
                (child.piggy_bank_balance / goal.target_amount * Decimal("100")).quantize(
                    Decimal("1")
                )
            ),
        )
        goal_read = SavingsGoalRead(
            id=goal.id,
            name=goal.name,
            emoji=goal.emoji,
            target_amount=goal.target_amount,
            current_amount=child.piggy_bank_balance,
            progress_percent=percent,
        )
    hour = datetime.now(ZoneInfo(timezone_name)).hour
    if hour < 12:
        greeting = "Good Morning! 👋"
    elif hour < 17:
        greeting = "Good Afternoon! 👋"
    else:
        greeting = "Good Evening! 👋"
    return KidDashboard(
        child_id=child.id,
        child_name=child.name,
        greeting=greeting,
        date=today,
        points_balance=child.points_balance,
        piggy_bank_balance=child.piggy_bank_balance,
        xoxo_balance=child.xoxo_balance,
        piggy_bank_interest_rate=child.piggy_bank_interest_rate,
        point_activity=[PointActivityRead.model_validate(item) for item in point_activity],
        chores=[
            ChoreRead.model_validate(chore).model_copy(
                update={
                    "completed": (chore.id, today) in completed,
                    "skip_status": (
                        cast(SkipStatus, today_skip_by_chore[chore.id].status)
                        if chore.id in today_skip_by_chore
                        else None
                    ),
                }
            )
            for chore in due
        ],
        completed_count=sum((chore.id, today) in completed for chore in required_due),
        total_count=len(required_due),
        rewards=[RewardRead.model_validate(reward) for reward in rewards],
        savings_goal=goal_read,
        streak_days=calculate_streak(chores, completed, approved_skips, today),
        pending_reward_count=pending_count,
    )


def _validate_history_date(day: date, timezone_name: str) -> None:
    if day > household_today(timezone_name):
        raise HTTPException(status_code=400, detail="Future dates are not available")


def build_daily_record(session: Session, day: date, timezone_name: str) -> DailyRecord:
    _validate_history_date(day, timezone_name)
    child = first_child(session)
    chores = list(
        session.scalars(
            select(Chore).where(Chore.child_id == child.id).order_by(Chore.created_at, Chore.id)
        )
    )
    completions = list(
        session.scalars(
            select(ChoreCompletion)
            .options(selectinload(ChoreCompletion.chore))
            .where(
                ChoreCompletion.child_id == child.id,
                ChoreCompletion.completion_date == day,
            )
        )
    )
    completion_by_chore = {completion.chore_id: completion for completion in completions}
    skip_requests = list(
        session.scalars(
            select(ChoreSkipRequest)
            .options(selectinload(ChoreSkipRequest.chore))
            .where(
                ChoreSkipRequest.child_id == child.id,
                ChoreSkipRequest.skip_date == day,
            )
        )
    )
    skip_by_chore = {request.chore_id: request for request in skip_requests}
    visible = {chore.id: chore for chore in chores if chore_occurs_on(chore, day)}
    for completed_chore in completions:
        visible[completed_chore.chore_id] = completed_chore.chore
    for skip_request in skip_requests:
        visible[skip_request.chore_id] = skip_request.chore

    day_chores = []
    for chore in visible.values():
        current_completion = completion_by_chore.get(chore.id)
        day_chores.append(
            DayChoreRead(
                id=chore.id,
                name=chore.name,
                emoji=chore.emoji,
                day_part=cast(DayPart, chore.day_part),
                completed=current_completion is not None,
                points_awarded=(
                    current_completion.points_awarded if current_completion else chore.points
                ),
                money_awarded=(
                    current_completion.money_awarded if current_completion else chore.money_reward
                ),
                xoxos_awarded=(
                    current_completion.xoxos_awarded if current_completion else chore.xoxo_reward
                ),
                skip_status=(
                    cast(SkipStatus, skip_by_chore[chore.id].status)
                    if chore.id in skip_by_chore
                    else None
                ),
            )
        )
    return DailyRecord(
        date=day,
        completed_count=sum(
            chore.completed for chore in day_chores if chore.skip_status != "approved"
        ),
        total_count=sum(chore.skip_status != "approved" for chore in day_chores),
        chores=day_chores,
    )


def build_week_record(session: Session, anchor: date, timezone_name: str) -> WeekRecord:
    today = household_today(timezone_name)
    sunday_offset = (anchor.weekday() + 1) % 7
    start = anchor - timedelta(days=sunday_offset)
    summaries = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        if day > today:
            summaries.append(
                WeekDaySummary(date=day, completed_count=0, total_count=0, future=True)
            )
            continue
        record = build_daily_record(session, day, timezone_name)
        summaries.append(
            WeekDaySummary(
                date=day,
                completed_count=record.completed_count,
                total_count=record.total_count,
            )
        )
    return WeekRecord(
        start_date=start,
        end_date=start + timedelta(days=6),
        days=summaries,
    )


def build_parent_daily_record(session: Session, day: date, timezone_name: str) -> ParentDailyRecord:
    record = build_daily_record(session, day, timezone_name)
    child = first_child(session)
    audit = list(
        session.scalars(
            select(ChoreAuditEvent)
            .where(
                ChoreAuditEvent.child_id == child.id,
                ChoreAuditEvent.effective_date == day,
            )
            .order_by(ChoreAuditEvent.created_at.desc(), ChoreAuditEvent.id.desc())
        )
    )
    return ParentDailyRecord(
        **record.model_dump(),
        audit=[ChoreAuditRead.model_validate(event) for event in audit],
    )


@dataclass(frozen=True)
class CompletionAward:
    points_awarded: int
    money_awarded: Decimal
    xoxos_awarded: int
    points_balance: int
    piggy_bank_balance: Decimal
    xoxo_balance: int


def complete_chore(
    session: Session,
    chore_id: object,
    timezone_name: str,
    *,
    completion_date: date | None = None,
    actor: str = "kid",
    audit_reason: str = "Completed in kid dashboard",
) -> CompletionAward:
    child = first_child(session, lock=True)
    today = completion_date or household_today(timezone_name)
    _validate_history_date(today, timezone_name)
    chore = session.scalar(
        select(Chore).where(Chore.id == chore_id, Chore.child_id == child.id).with_for_update()
    )
    if chore is None or not chore_occurs_on(chore, today):
        raise HTTPException(status_code=404, detail="Chore is not available on this date")
    skip_request = session.scalar(
        select(ChoreSkipRequest)
        .where(
            ChoreSkipRequest.chore_id == chore.id,
            ChoreSkipRequest.child_id == child.id,
            ChoreSkipRequest.skip_date == today,
        )
        .with_for_update()
    )
    if skip_request is not None and skip_request.status == "pending":
        raise HTTPException(
            status_code=409,
            detail="This chore has a skip request waiting for parent approval",
        )
    if skip_request is not None and skip_request.status == "approved":
        raise HTTPException(status_code=409, detail="This chore was skipped for this date")
    existing = session.scalar(
        select(ChoreCompletion.id).where(
            ChoreCompletion.chore_id == chore.id,
            ChoreCompletion.child_id == child.id,
            ChoreCompletion.completion_date == today,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Chore is already complete on this date")
    completion = ChoreCompletion(
        chore_id=chore.id,
        child_id=child.id,
        completion_date=today,
        points_awarded=chore.points,
        money_awarded=chore.money_reward,
        xoxos_awarded=chore.xoxo_reward,
    )
    session.add(completion)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Chore is already complete on this date"
        ) from error
    reason = f"Completed {chore.name}"
    session.add(
        ChoreAuditEvent(
            child_id=child.id,
            chore_id=chore.id,
            chore_name=chore.name,
            effective_date=today,
            action="completed",
            actor=actor,
            points_delta=chore.points,
            money_delta=chore.money_reward,
            xoxos_delta=chore.xoxo_reward,
            reason=audit_reason,
            created_at=datetime.now(UTC),
        )
    )
    if chore.points:
        session.add(
            PointTransaction(
                child_id=child.id,
                amount=chore.points,
                reason=reason,
                source_type="chore_completion",
                source_id=completion.id,
            )
        )
        child.points_balance += chore.points
    if chore.money_reward:
        session.add(
            PiggyBankTransaction(
                child_id=child.id,
                amount=chore.money_reward,
                reason=reason,
            )
        )
        child.piggy_bank_balance = (child.piggy_bank_balance + chore.money_reward).quantize(
            Decimal("0.01")
        )
    if chore.xoxo_reward:
        session.add(
            XoxoTransaction(
                child_id=child.id,
                amount=chore.xoxo_reward,
                reason=reason,
            )
        )
        child.xoxo_balance += chore.xoxo_reward
    session.commit()
    return CompletionAward(
        points_awarded=chore.points,
        money_awarded=chore.money_reward,
        xoxos_awarded=chore.xoxo_reward,
        points_balance=child.points_balance,
        piggy_bank_balance=child.piggy_bank_balance,
        xoxo_balance=child.xoxo_balance,
    )


def reopen_historical_chore(
    session: Session,
    chore_id: object,
    day: date,
    timezone_name: str,
    reason: str,
    *,
    actor: Literal["kid", "parent"] = "parent",
) -> None:
    _validate_history_date(day, timezone_name)
    child = first_child(session, lock=True)
    completion = session.scalar(
        select(ChoreCompletion)
        .options(selectinload(ChoreCompletion.chore))
        .where(
            ChoreCompletion.chore_id == chore_id,
            ChoreCompletion.child_id == child.id,
            ChoreCompletion.completion_date == day,
        )
        .with_for_update()
    )
    if completion is None:
        raise HTTPException(status_code=409, detail="Chore is not complete on this date")
    new_points = child.points_balance - completion.points_awarded
    new_money = (child.piggy_bank_balance - completion.money_awarded).quantize(Decimal("0.01"))
    new_xoxos = child.xoxo_balance - completion.xoxos_awarded
    if new_points < 0 or new_money < 0 or new_xoxos < 0:
        raise HTTPException(
            status_code=409,
            detail="This completion cannot be undone because part of its award has been spent",
        )

    audit_id = uuid4()
    ledger_action = "Undid" if actor == "kid" else "Reopened"
    ledger_reason = f"{ledger_action} {completion.chore.name}: {reason}"
    session.add(
        ChoreAuditEvent(
            id=audit_id,
            child_id=child.id,
            chore_id=completion.chore_id,
            chore_name=completion.chore.name,
            effective_date=day,
            action="reopened",
            actor=actor,
            points_delta=-completion.points_awarded,
            money_delta=-completion.money_awarded,
            xoxos_delta=-completion.xoxos_awarded,
            reason=reason,
            created_at=datetime.now(UTC),
        )
    )
    if completion.points_awarded:
        session.add(
            PointTransaction(
                child_id=child.id,
                amount=-completion.points_awarded,
                reason=ledger_reason,
                source_type="chore_reversal",
                source_id=audit_id,
            )
        )
    if completion.money_awarded:
        session.add(
            PiggyBankTransaction(
                child_id=child.id,
                amount=-completion.money_awarded,
                reason=ledger_reason,
            )
        )
    if completion.xoxos_awarded:
        session.add(
            XoxoTransaction(
                child_id=child.id,
                amount=-completion.xoxos_awarded,
                reason=ledger_reason,
            )
        )
    child.points_balance = new_points
    child.piggy_bank_balance = new_money
    child.xoxo_balance = new_xoxos
    session.delete(completion)
    session.commit()


def adjust_points(session: Session, amount: int, reason: str) -> int:
    child = first_child(session, lock=True)
    new_balance = child.points_balance + amount
    if new_balance < 0:
        raise HTTPException(status_code=409, detail="Point balance cannot become negative")
    child.points_balance = new_balance
    session.add(
        PointTransaction(
            child_id=child.id,
            amount=amount,
            reason=reason,
            source_type="parent_adjustment",
        )
    )
    session.commit()
    return new_balance


def adjust_piggy_bank(session: Session, amount: Decimal, reason: str) -> Decimal:
    child = first_child(session, lock=True)
    new_balance = (child.piggy_bank_balance + amount).quantize(Decimal("0.01"))
    if new_balance < 0:
        raise HTTPException(status_code=409, detail="Piggy-bank balance cannot become negative")
    child.piggy_bank_balance = new_balance
    session.add(PiggyBankTransaction(child_id=child.id, amount=amount, reason=reason))
    session.commit()
    return new_balance


def adjust_xoxos(session: Session, amount: int, reason: str) -> int:
    child = first_child(session, lock=True)
    new_balance = child.xoxo_balance + amount
    if new_balance < 0:
        raise HTTPException(status_code=409, detail="XOXO balance cannot become negative")
    child.xoxo_balance = new_balance
    session.add(XoxoTransaction(child_id=child.id, amount=amount, reason=reason))
    session.commit()
    return new_balance


def set_interest_rate(session: Session, annual_rate: Decimal) -> Decimal:
    child = first_child(session, lock=True)
    child.piggy_bank_interest_rate = annual_rate.quantize(Decimal("0.01"))
    session.commit()
    return child.piggy_bank_interest_rate


def projected_balance(balance: Decimal, annual_rate: Decimal, months: int = 12) -> Decimal:
    monthly_rate = annual_rate / Decimal("1200")
    projected = balance
    for _ in range(months):
        projected = (projected * (Decimal("1") + monthly_rate)).quantize(Decimal("0.01"))
    return projected


def apply_monthly_interest(session: Session) -> tuple[Decimal, Decimal, Decimal]:
    child = first_child(session, lock=True)
    monthly_rate = child.piggy_bank_interest_rate / Decimal("1200")
    interest = (child.piggy_bank_balance * monthly_rate).quantize(Decimal("0.01"))
    if interest <= 0:
        raise HTTPException(
            status_code=409,
            detail="Set an interest rate and keep a positive balance before applying interest",
        )
    child.piggy_bank_balance = (child.piggy_bank_balance + interest).quantize(Decimal("0.01"))
    session.add(
        PiggyBankTransaction(
            child_id=child.id,
            amount=interest,
            reason=f"Monthly interest at {child.piggy_bank_interest_rate}% annual rate",
        )
    )
    session.commit()
    return (
        interest,
        child.piggy_bank_balance,
        projected_balance(child.piggy_bank_balance, child.piggy_bank_interest_rate),
    )


def request_reward(session: Session, reward_id: object) -> RewardRequest:
    child = first_child(session)
    reward = session.scalar(
        select(Reward).where(
            Reward.id == reward_id, Reward.child_id == child.id, Reward.active.is_(True)
        )
    )
    if reward is None:
        raise HTTPException(status_code=404, detail="Reward is not available")
    request = RewardRequest(
        reward_id=reward.id,
        child_id=child.id,
        status="pending",
        points_cost=reward.points_cost,
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def request_chore_skip(session: Session, chore_id: object, timezone_name: str) -> ChoreSkipRequest:
    child = first_child(session, lock=True)
    today = household_today(timezone_name)
    chore = session.scalar(
        select(Chore).where(Chore.id == chore_id, Chore.child_id == child.id).with_for_update()
    )
    if chore is None or not chore_occurs_on(chore, today):
        raise HTTPException(status_code=404, detail="Chore is not available today")
    completion = session.scalar(
        select(ChoreCompletion.id).where(
            ChoreCompletion.chore_id == chore.id,
            ChoreCompletion.child_id == child.id,
            ChoreCompletion.completion_date == today,
        )
    )
    if completion is not None:
        raise HTTPException(status_code=409, detail="Completed chores cannot be skipped")
    existing = session.scalar(
        select(ChoreSkipRequest).where(
            ChoreSkipRequest.chore_id == chore.id,
            ChoreSkipRequest.child_id == child.id,
            ChoreSkipRequest.skip_date == today,
        )
    )
    if existing is not None:
        messages = {
            "pending": "Skip request is already waiting for parent approval",
            "approved": "This chore is already skipped today",
            "rejected": "This skip request was already declined today",
        }
        raise HTTPException(status_code=409, detail=messages[existing.status])
    request = ChoreSkipRequest(
        chore_id=chore.id,
        child_id=child.id,
        skip_date=today,
        status="pending",
    )
    session.add(request)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Skip request is already waiting for parent approval",
        ) from error
    session.refresh(request)
    return request


def resolve_chore_skip_request(
    session: Session, request_id: object, action: str
) -> ChoreSkipRequest:
    request = session.scalar(
        select(ChoreSkipRequest)
        .options(selectinload(ChoreSkipRequest.chore))
        .where(ChoreSkipRequest.id == request_id)
        .with_for_update()
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Skip request not found")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="Skip request has already been resolved")
    if action == "approve":
        completion = session.scalar(
            select(ChoreCompletion.id).where(
                ChoreCompletion.chore_id == request.chore_id,
                ChoreCompletion.child_id == request.child_id,
                ChoreCompletion.completion_date == request.skip_date,
            )
        )
        if completion is not None:
            raise HTTPException(status_code=409, detail="A completed chore cannot be skipped")
        request.status = "approved"
    else:
        request.status = "rejected"
    request.resolved_at = datetime.now(UTC)
    session.commit()
    return request


def archive_chore(session: Session, chore_id: object) -> None:
    child = first_child(session)
    chore = session.scalar(
        select(Chore).where(Chore.id == chore_id, Chore.child_id == child.id).with_for_update()
    )
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    chore.active = False
    session.commit()


def delete_chore(session: Session, chore_id: object) -> None:
    child = first_child(session)
    chore = session.scalar(
        select(Chore).where(Chore.id == chore_id, Chore.child_id == child.id).with_for_update()
    )
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    if chore.active:
        raise HTTPException(status_code=409, detail="Archive the chore before deleting it")
    has_history = session.scalar(
        select(ChoreCompletion.id).where(ChoreCompletion.chore_id == chore.id).limit(1)
    )
    if has_history is None:
        has_history = session.scalar(
            select(ChoreAuditEvent.id).where(ChoreAuditEvent.chore_id == chore.id).limit(1)
        )
    if has_history is None:
        has_history = session.scalar(
            select(ChoreSkipRequest.id).where(ChoreSkipRequest.chore_id == chore.id).limit(1)
        )
    if has_history is not None:
        raise HTTPException(
            status_code=409,
            detail="This chore has completion history and must remain archived",
        )
    session.delete(chore)
    session.commit()


def archive_reward(session: Session, reward_id: object) -> None:
    child = first_child(session)
    reward = session.scalar(
        select(Reward).where(Reward.id == reward_id, Reward.child_id == child.id).with_for_update()
    )
    if reward is None:
        raise HTTPException(status_code=404, detail="Reward not found")
    reward.active = False
    session.commit()


def resolve_reward_request(session: Session, request_id: object, action: str) -> RewardRequest:
    request = session.scalar(
        select(RewardRequest)
        .options(selectinload(RewardRequest.reward))
        .where(RewardRequest.id == request_id)
        .with_for_update()
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Reward request not found")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="Reward request has already been resolved")
    child = session.scalar(select(Child).where(Child.id == request.child_id).with_for_update())
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    if action == "approve":
        if child.points_balance < request.points_cost:
            raise HTTPException(status_code=409, detail="Not enough points to approve this reward")
        child.points_balance -= request.points_cost
        session.add(
            PointTransaction(
                child_id=child.id,
                amount=-request.points_cost,
                reason=f"Approved reward: {request.reward.name}",
                source_type="reward_request",
                source_id=request.id,
            )
        )
        request.status = "approved"
    else:
        request.status = "rejected"
    request.resolved_at = datetime.now(UTC)
    session.commit()
    return request


def build_parent_overview(session: Session, timezone_name: str) -> ParentOverview:
    dashboard = build_dashboard(session, timezone_name)
    child_id = dashboard.child_id
    chores = list(
        session.scalars(select(Chore).where(Chore.child_id == child_id).order_by(Chore.name))
    )
    rewards = list(
        session.scalars(select(Reward).where(Reward.child_id == child_id).order_by(Reward.name))
    )
    requests = list(
        session.scalars(
            select(RewardRequest)
            .options(selectinload(RewardRequest.reward))
            .where(RewardRequest.child_id == child_id)
            .order_by(RewardRequest.requested_at.desc())
        )
    )
    skip_requests = list(
        session.scalars(
            select(ChoreSkipRequest)
            .options(selectinload(ChoreSkipRequest.chore))
            .where(ChoreSkipRequest.child_id == child_id)
            .order_by(ChoreSkipRequest.requested_at.desc())
        )
    )
    point_history = list(
        session.scalars(
            select(PointTransaction)
            .where(PointTransaction.child_id == child_id)
            .order_by(PointTransaction.created_at.desc())
            .limit(50)
        )
    )
    piggy_history = list(
        session.scalars(
            select(PiggyBankTransaction)
            .where(PiggyBankTransaction.child_id == child_id)
            .order_by(PiggyBankTransaction.created_at.desc())
            .limit(50)
        )
    )
    xoxo_history = list(
        session.scalars(
            select(XoxoTransaction)
            .where(XoxoTransaction.child_id == child_id)
            .order_by(XoxoTransaction.created_at.desc())
            .limit(50)
        )
    )
    return ParentOverview(
        dashboard=dashboard,
        all_chores=[ChoreRead.model_validate(chore) for chore in chores],
        all_rewards=[RewardRead.model_validate(reward) for reward in rewards],
        reward_requests=[_reward_request_read(request) for request in requests],
        skip_requests=[_skip_request_read(request) for request in skip_requests],
        point_history=[PointTransactionRead.model_validate(item) for item in point_history],
        piggy_bank_history=[PiggyTransactionRead.model_validate(item) for item in piggy_history],
        xoxo_history=[XoxoTransactionRead.model_validate(item) for item in xoxo_history],
    )
