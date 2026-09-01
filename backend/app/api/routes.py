from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.security import (
    PARENT_COOKIE,
    change_configured_pin,
    create_parent_token,
    require_parent,
    verify_configured_pin,
)
from app.db.session import get_db
from app.models import Chore, ChoreSkipRequest, Reward, RewardRequest, SavingsGoal
from app.schemas.contracts import (
    AdjustmentWrite,
    BalanceResult,
    ChoreRead,
    ChoreSkipRequestRead,
    ChoreWrite,
    CompletionResult,
    DailyRecord,
    HistoricalCompletionWrite,
    InterestRateWrite,
    InterestResult,
    KidDashboard,
    MoneyAdjustmentWrite,
    ParentDailyRecord,
    ParentOverview,
    PinChange,
    PinLogin,
    RewardRead,
    RewardRequestCreate,
    RewardRequestRead,
    RewardResolution,
    RewardWrite,
    SavingsGoalRead,
    SavingsGoalWrite,
    SkipResolution,
    WeatherRead,
    WeekRecord,
)
from app.services.chores import (
    adjust_piggy_bank,
    adjust_points,
    adjust_xoxos,
    apply_monthly_interest,
    archive_chore,
    archive_reward,
    build_daily_record,
    build_dashboard,
    build_parent_daily_record,
    build_parent_overview,
    build_week_record,
    complete_chore,
    delete_chore,
    first_child,
    household_today,
    projected_balance,
    reopen_historical_chore,
    request_chore_skip,
    request_reward,
    resolve_chore_skip_request,
    resolve_reward_request,
    set_interest_rate,
)
from app.services.weather import WeatherLocation, configured_weather

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
ParentAccess = Annotated[None, Depends(require_parent)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=KidDashboard)
def dashboard(session: DbSession, settings: SettingsDependency) -> KidDashboard:
    return build_dashboard(session, settings.household_timezone)


@router.get("/days/{day}", response_model=DailyRecord)
def daily_record(day: date, session: DbSession, settings: SettingsDependency) -> DailyRecord:
    return build_daily_record(session, day, settings.household_timezone)


@router.get("/weeks/{day}", response_model=WeekRecord)
def week_record(day: date, session: DbSession, settings: SettingsDependency) -> WeekRecord:
    return build_week_record(session, day, settings.household_timezone)


@router.get("/weather", response_model=list[WeatherRead])
def weather(settings: SettingsDependency) -> list[WeatherRead]:
    return configured_weather(
        [
            WeatherLocation("home", settings.weather_home_label, settings.weather_home_location),
            WeatherLocation(
                "school", settings.weather_school_label, settings.weather_school_location
            ),
        ]
    )


@router.post("/chores/{chore_id}/complete", response_model=CompletionResult)
def mark_chore_complete(
    chore_id: UUID, session: DbSession, settings: SettingsDependency
) -> CompletionResult:
    award = complete_chore(session, chore_id, settings.household_timezone)
    reward_parts = []
    if award.points_awarded:
        reward_parts.append(f"+{award.points_awarded} ⭐")
    if award.money_awarded:
        reward_parts.append(f"+${award.money_awarded:.2f}")
    if award.xoxos_awarded:
        reward_parts.append(f"+{award.xoxos_awarded} 🤗")
    return CompletionResult(
        chore_id=chore_id,
        points_awarded=award.points_awarded,
        money_awarded=award.money_awarded,
        xoxos_awarded=award.xoxos_awarded,
        points_balance=award.points_balance,
        piggy_bank_balance=award.piggy_bank_balance,
        xoxo_balance=award.xoxo_balance,
        message=f"Great job! {' · '.join(reward_parts)}",
    )


@router.post(
    "/chores/{chore_id}/skip-requests",
    response_model=ChoreSkipRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chore_skip_request(
    chore_id: UUID, session: DbSession, settings: SettingsDependency
) -> ChoreSkipRequestRead:
    request = request_chore_skip(session, chore_id, settings.household_timezone)
    chore = session.get(Chore, request.chore_id)
    if chore is None:  # pragma: no cover - protected by the foreign key
        raise HTTPException(status_code=500, detail="Chore could not be loaded")
    return ChoreSkipRequestRead(
        id=request.id,
        chore_id=request.chore_id,
        chore_name=chore.name,
        chore_emoji=chore.emoji,
        skip_date=request.skip_date,
        status="pending",
        requested_at=request.requested_at,
        resolved_at=None,
    )


@router.delete("/chores/{chore_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
def undo_chore_complete(chore_id: UUID, session: DbSession, settings: SettingsDependency) -> None:
    reopen_historical_chore(
        session,
        chore_id,
        household_today(settings.household_timezone),
        settings.household_timezone,
        "Undone in kid dashboard",
        actor="kid",
    )


@router.post(
    "/reward-requests", response_model=RewardRequestRead, status_code=status.HTTP_201_CREATED
)
def create_reward_request(payload: RewardRequestCreate, session: DbSession) -> RewardRequestRead:
    request = request_reward(session, payload.reward_id)
    reward = session.get(Reward, request.reward_id)
    if reward is None:  # pragma: no cover - protected by the foreign key
        raise HTTPException(status_code=500, detail="Reward could not be loaded")
    return RewardRequestRead(
        id=request.id,
        reward_id=request.reward_id,
        reward_name=reward.name,
        reward_emoji=reward.emoji,
        status="pending",
        points_cost=request.points_cost,
        requested_at=request.requested_at,
        resolved_at=None,
    )


@router.post("/parent/login", status_code=status.HTTP_204_NO_CONTENT)
def parent_login(
    payload: PinLogin, response: Response, settings: SettingsDependency, session: DbSession
) -> None:
    if not verify_configured_pin(session, payload.pin, settings.parent_pin):
        raise HTTPException(status_code=401, detail="Incorrect parent PIN")
    response.set_cookie(
        key=PARENT_COOKIE,
        value=create_parent_token(settings),
        max_age=settings.parent_session_seconds,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/",
    )


@router.post("/parent/logout", status_code=status.HTTP_204_NO_CONTENT)
def parent_logout(response: Response) -> None:
    response.delete_cookie(PARENT_COOKIE, path="/")


@router.get("/parent/session", status_code=status.HTTP_204_NO_CONTENT)
def parent_session(_: ParentAccess) -> None:
    return None


@router.put("/parent/pin", status_code=status.HTTP_204_NO_CONTENT)
def change_parent_pin(
    payload: PinChange,
    response: Response,
    settings: SettingsDependency,
    session: DbSession,
    _: ParentAccess,
) -> None:
    if not verify_configured_pin(session, payload.current_pin, settings.parent_pin):
        raise HTTPException(status_code=401, detail="Current PIN is incorrect")
    change_configured_pin(session, payload.new_pin)
    response.delete_cookie(PARENT_COOKIE, path="/")


@router.get("/parent/overview", response_model=ParentOverview)
def parent_overview(
    session: DbSession, settings: SettingsDependency, _: ParentAccess
) -> ParentOverview:
    return build_parent_overview(session, settings.household_timezone)


@router.get("/parent/days/{day}", response_model=ParentDailyRecord)
def parent_daily_record(
    day: date, session: DbSession, settings: SettingsDependency, _: ParentAccess
) -> ParentDailyRecord:
    return build_parent_daily_record(session, day, settings.household_timezone)


@router.put(
    "/parent/days/{day}/chores/{chore_id}",
    response_model=ParentDailyRecord,
)
def update_historical_completion(
    day: date,
    chore_id: UUID,
    payload: HistoricalCompletionWrite,
    session: DbSession,
    settings: SettingsDependency,
    _: ParentAccess,
) -> ParentDailyRecord:
    if payload.completed:
        complete_chore(
            session,
            chore_id,
            settings.household_timezone,
            completion_date=day,
            actor="parent",
            audit_reason=payload.reason,
        )
    else:
        reopen_historical_chore(
            session,
            chore_id,
            day,
            settings.household_timezone,
            payload.reason,
        )
    return build_parent_daily_record(session, day, settings.household_timezone)


@router.post("/parent/chores", response_model=ChoreRead, status_code=status.HTTP_201_CREATED)
def create_chore(payload: ChoreWrite, session: DbSession, _: ParentAccess) -> Chore:
    child = first_child(session)
    chore = Chore(child_id=child.id, **payload.model_dump())
    session.add(chore)
    session.commit()
    session.refresh(chore)
    return chore


@router.put("/parent/chores/{chore_id}", response_model=ChoreRead)
def update_chore(chore_id: UUID, payload: ChoreWrite, session: DbSession, _: ParentAccess) -> Chore:
    child = first_child(session)
    chore = session.scalar(select(Chore).where(Chore.id == chore_id, Chore.child_id == child.id))
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    for field, value in payload.model_dump().items():
        setattr(chore, field, value)
    session.commit()
    session.refresh(chore)
    return chore


@router.delete("/parent/chores/{chore_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_chore_route(chore_id: UUID, session: DbSession, _: ParentAccess) -> None:
    archive_chore(session, chore_id)


@router.delete("/parent/chores/{chore_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
def delete_chore_route(chore_id: UUID, session: DbSession, _: ParentAccess) -> None:
    delete_chore(session, chore_id)


@router.post("/parent/points", response_model=BalanceResult)
def change_points(payload: AdjustmentWrite, session: DbSession, _: ParentAccess) -> BalanceResult:
    return BalanceResult(balance=adjust_points(session, payload.amount, payload.reason))


@router.post("/parent/piggy-bank", response_model=BalanceResult)
def change_piggy_bank(
    payload: MoneyAdjustmentWrite, session: DbSession, _: ParentAccess
) -> BalanceResult:
    return BalanceResult(balance=adjust_piggy_bank(session, payload.amount, payload.reason))


@router.post("/parent/xoxos", response_model=BalanceResult)
def change_xoxos(payload: AdjustmentWrite, session: DbSession, _: ParentAccess) -> BalanceResult:
    return BalanceResult(balance=adjust_xoxos(session, payload.amount, payload.reason))


@router.put("/parent/piggy-bank/interest-rate", response_model=InterestResult)
def change_interest_rate(
    payload: InterestRateWrite, session: DbSession, _: ParentAccess
) -> InterestResult:
    annual_rate = set_interest_rate(session, payload.annual_rate)
    child = first_child(session)
    return InterestResult(
        annual_rate=annual_rate,
        interest_earned=Decimal("0.00"),
        balance=child.piggy_bank_balance,
        projected_one_year=projected_balance(child.piggy_bank_balance, annual_rate),
    )


@router.post("/parent/piggy-bank/apply-interest", response_model=InterestResult)
def add_monthly_interest(session: DbSession, _: ParentAccess) -> InterestResult:
    earned, balance, projected = apply_monthly_interest(session)
    child = first_child(session)
    return InterestResult(
        annual_rate=child.piggy_bank_interest_rate,
        interest_earned=earned,
        balance=balance,
        projected_one_year=projected,
    )


@router.post("/parent/rewards", response_model=RewardRead, status_code=status.HTTP_201_CREATED)
def create_reward(payload: RewardWrite, session: DbSession, _: ParentAccess) -> Reward:
    child = first_child(session)
    reward = Reward(child_id=child.id, **payload.model_dump())
    session.add(reward)
    session.commit()
    session.refresh(reward)
    return reward


@router.put("/parent/rewards/{reward_id}", response_model=RewardRead)
def update_reward(
    reward_id: UUID, payload: RewardWrite, session: DbSession, _: ParentAccess
) -> Reward:
    child = first_child(session)
    reward = session.scalar(
        select(Reward).where(Reward.id == reward_id, Reward.child_id == child.id)
    )
    if reward is None:
        raise HTTPException(status_code=404, detail="Reward not found")
    for field, value in payload.model_dump().items():
        setattr(reward, field, value)
    session.commit()
    session.refresh(reward)
    return reward


@router.delete("/parent/rewards/{reward_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_reward_route(reward_id: UUID, session: DbSession, _: ParentAccess) -> None:
    archive_reward(session, reward_id)


@router.patch(
    "/parent/chore-skip-requests/{request_id}",
    response_model=ChoreSkipRequestRead,
)
def decide_chore_skip_request(
    request_id: UUID, payload: SkipResolution, session: DbSession, _: ParentAccess
) -> ChoreSkipRequestRead:
    request = resolve_chore_skip_request(session, request_id, payload.action)
    loaded = session.scalar(
        select(ChoreSkipRequest)
        .options(selectinload(ChoreSkipRequest.chore))
        .where(ChoreSkipRequest.id == request.id)
    )
    if loaded is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Skip request could not be loaded")
    return ChoreSkipRequestRead(
        id=loaded.id,
        chore_id=loaded.chore_id,
        chore_name=loaded.chore.name,
        chore_emoji=loaded.chore.emoji,
        skip_date=loaded.skip_date,
        status=loaded.status,  # type: ignore[arg-type]
        requested_at=loaded.requested_at,
        resolved_at=loaded.resolved_at,
    )


@router.patch("/parent/reward-requests/{request_id}", response_model=RewardRequestRead)
def decide_reward_request(
    request_id: UUID, payload: RewardResolution, session: DbSession, _: ParentAccess
) -> RewardRequestRead:
    request = resolve_reward_request(session, request_id, payload.action)
    loaded = session.scalar(
        select(RewardRequest)
        .options(selectinload(RewardRequest.reward))
        .where(RewardRequest.id == request.id)
    )
    if loaded is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Reward request could not be loaded")
    return RewardRequestRead(
        id=loaded.id,
        reward_id=loaded.reward_id,
        reward_name=loaded.reward.name,
        reward_emoji=loaded.reward.emoji,
        status=loaded.status,  # type: ignore[arg-type]
        points_cost=loaded.points_cost,
        requested_at=loaded.requested_at,
        resolved_at=loaded.resolved_at,
    )


@router.put("/parent/savings-goal", response_model=SavingsGoalRead)
def save_goal(payload: SavingsGoalWrite, session: DbSession, _: ParentAccess) -> SavingsGoalRead:
    child = first_child(session)
    goal = session.scalar(select(SavingsGoal).where(SavingsGoal.child_id == child.id))
    if goal is None:
        goal = SavingsGoal(child_id=child.id, **payload.model_dump())
        session.add(goal)
    else:
        for field, value in payload.model_dump().items():
            setattr(goal, field, value)
    session.commit()
    session.refresh(goal)
    percent = min(100, int(child.piggy_bank_balance / goal.target_amount * 100))
    return SavingsGoalRead(
        id=goal.id,
        name=goal.name,
        emoji=goal.emoji,
        target_amount=goal.target_amount,
        current_amount=child.piggy_bank_balance,
        progress_percent=percent,
    )
