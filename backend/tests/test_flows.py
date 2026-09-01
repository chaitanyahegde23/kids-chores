from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import (
    Child,
    Chore,
    ChoreAuditEvent,
    ChoreCompletion,
    ChoreSkipRequest,
    HouseholdSecurity,
    PiggyBankTransaction,
    PointTransaction,
    Reward,
    RewardRequest,
    XoxoTransaction,
)
from app.services.chores import chore_occurs_on
from app.services.weather import WeatherLocation, current_weather, resolve_location


def test_main_dashboard_renders_seed_data(client: TestClient) -> None:
    response = client.get("/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["child_name"] == "Kid"
    assert payload["points_balance"] == 1250
    assert payload["piggy_bank_balance"] == "84.00"
    assert payload["xoxo_balance"] == 0
    assert payload["piggy_bank_interest_rate"] == "0.00"
    assert len(payload["chores"]) == 4
    assert len(payload["rewards"]) == 4
    assert payload["savings_goal"]["name"] == "LEGO Set"
    assert payload["point_activity"][0]["amount"] == 1250
    assert payload["point_activity"][0]["reason"] == "Demo starting balance"


def test_week_summary_runs_sunday_through_saturday(client: TestClient) -> None:
    today = client.get("/dashboard").json()["date"]

    response = client.get(f"/weeks/{today}")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["days"]) == 7
    assert date.fromisoformat(payload["start_date"]).weekday() == 6
    assert date.fromisoformat(payload["end_date"]) - date.fromisoformat(
        payload["start_date"]
    ) == timedelta(days=6)
    assert next(day for day in payload["days"] if day["date"] == today)["future"] is False


def test_weather_maps_daily_local_forecast() -> None:
    response = BytesIO(
        b'{"current":{"temperature_2m":71.6,"weather_code":1},'
        b'"daily":{"temperature_2m_max":[78.2],"temperature_2m_min":[55.7]}}'
    )
    with (
        patch(
            "app.services.weather.resolve_location",
            return_value=(40.75, -73.99, "New York, New York"),
        ),
        patch("app.services.weather.urlopen", return_value=response),
    ):
        weather = current_weather(WeatherLocation("home", "Home", "10001"))

    assert weather.key == "home"
    assert weather.name == "Home"
    assert weather.location == "New York, New York"
    assert weather.temperature == 72
    assert weather.high == 78
    assert weather.low == 56
    assert weather.label == "Mostly clear"


def test_weather_location_resolves_a_configured_postal_code() -> None:
    response = BytesIO(
        b'{"results":[{"name":"New York","admin1":"New York","latitude":40.75,"longitude":-73.99}]}'
    )
    resolve_location.cache_clear()
    with patch("app.services.weather.urlopen", return_value=response) as mocked_open:
        result = resolve_location("10001")

    assert result == (40.75, -73.99, "New York")
    assert "name=10001" in mocked_open.call_args.args[0]


def test_chore_completion_awards_all_configured_values_and_creates_ledgers(
    parent_client: TestClient, session: Session
) -> None:
    created = parent_client.post(
        "/parent/chores",
        json={
            "name": "Multi reward chore",
            "emoji": "✨",
            "points": 7,
            "money_reward": "0.25",
            "xoxo_reward": 2,
            "recurrence_type": "daily",
        },
    )
    assert created.status_code == 201
    chore_id = created.json()["id"]

    response = parent_client.post(f"/chores/{chore_id}/complete")

    assert response.status_code == 200
    assert response.json() == {
        "chore_id": chore_id,
        "points_awarded": 7,
        "money_awarded": "0.25",
        "xoxos_awarded": 2,
        "points_balance": 1257,
        "piggy_bank_balance": "84.25",
        "xoxo_balance": 2,
        "message": "Great job! +7 ⭐ · +$0.25 · +2 🤗",
    }
    child = session.scalar(select(Child))
    assert child is not None
    assert child.points_balance == 1257
    assert child.piggy_bank_balance == Decimal("84.25")
    assert child.xoxo_balance == 2
    point_transaction = session.scalar(
        select(PointTransaction).where(PointTransaction.reason == "Completed Multi reward chore")
    )
    money_transaction = session.scalar(
        select(PiggyBankTransaction).where(
            PiggyBankTransaction.reason == "Completed Multi reward chore"
        )
    )
    xoxo_transaction = session.scalar(
        select(XoxoTransaction).where(XoxoTransaction.reason == "Completed Multi reward chore")
    )
    assert point_transaction is not None and point_transaction.amount == 7
    assert money_transaction is not None and money_transaction.amount == Decimal("0.25")
    assert xoxo_transaction is not None and xoxo_transaction.amount == 2


def test_same_chore_cannot_award_points_twice(client: TestClient, session: Session) -> None:
    chore = client.get("/dashboard").json()["chores"][0]
    chore_id = chore["id"]

    assert client.post(f"/chores/{chore_id}/complete").status_code == 200
    duplicate = client.post(f"/chores/{chore_id}/complete")

    assert duplicate.status_code == 409
    child = session.scalar(select(Child))
    assert child is not None and child.points_balance == 1250 + chore["points"]
    awarded = list(
        session.scalars(
            select(PointTransaction).where(PointTransaction.source_type == "chore_completion")
        )
    )
    assert len(awarded) == 1


def test_kid_can_undo_todays_chore_and_reverse_all_awards(
    client: TestClient, session: Session
) -> None:
    child = session.scalar(select(Child))
    assert child is not None
    chore = Chore(
        child_id=child.id,
        name="Undoable chore",
        emoji="↩️",
        points=7,
        money_reward=Decimal("0.25"),
        xoxo_reward=2,
        recurrence_type="daily",
        day_part="after_school",
    )
    session.add(chore)
    session.commit()

    assert client.post(f"/chores/{chore.id}/complete").status_code == 200
    response = client.delete(f"/chores/{chore.id}/complete")

    assert response.status_code == 204
    assert child.points_balance == 1250
    assert child.piggy_bank_balance == Decimal("84.00")
    assert child.xoxo_balance == 0
    assert (
        session.scalar(select(ChoreCompletion).where(ChoreCompletion.chore_id == chore.id)) is None
    )
    reversal = session.scalar(
        select(PointTransaction).where(
            PointTransaction.source_type == "chore_reversal",
            PointTransaction.amount == -7,
        )
    )
    assert reversal is not None and reversal.reason == (
        "Undid Undoable chore: Undone in kid dashboard"
    )
    audit = session.scalar(
        select(ChoreAuditEvent).where(
            ChoreAuditEvent.chore_id == chore.id,
            ChoreAuditEvent.action == "reopened",
        )
    )
    assert audit is not None and audit.actor == "kid"
    assert client.delete(f"/chores/{chore.id}/complete").status_code == 409


def test_kid_undo_is_rejected_when_award_has_been_spent(
    parent_client: TestClient, session: Session
) -> None:
    chore = parent_client.get("/dashboard").json()["chores"][0]
    assert parent_client.post(f"/chores/{chore['id']}/complete").status_code == 200
    balance = parent_client.get("/dashboard").json()["points_balance"]
    assert (
        parent_client.post(
            "/parent/points",
            json={"amount": -(balance - 1), "reason": "Synthetic spending before undo"},
        ).status_code
        == 200
    )

    response = parent_client.delete(f"/chores/{chore['id']}/complete")

    assert response.status_code == 409
    assert "spent" in response.json()["detail"]
    completion = session.scalar(
        select(ChoreCompletion).where(ChoreCompletion.chore_id == UUID(chore["id"]))
    )
    assert completion is not None


def test_archiving_chore_preserves_completion_history(
    parent_client: TestClient, session: Session
) -> None:
    chore_id = parent_client.get("/dashboard").json()["chores"][0]["id"]
    assert parent_client.post(f"/chores/{chore_id}/complete").status_code == 200

    response = parent_client.delete(f"/parent/chores/{chore_id}")

    assert response.status_code == 204
    chore = session.get(Chore, UUID(chore_id))
    assert chore is not None and not chore.active
    completion = session.scalar(
        select(ChoreCompletion).where(ChoreCompletion.chore_id == UUID(chore_id))
    )
    assert completion is not None
    assert all(item["id"] != chore_id for item in parent_client.get("/dashboard").json()["chores"])


def test_parent_can_create_then_archive_and_delete_unused_chore(
    parent_client: TestClient, session: Session
) -> None:
    created = parent_client.post(
        "/parent/chores",
        json={"name": "Test chore", "emoji": "🧪", "points": 5, "recurrence_type": "daily"},
    )
    assert created.status_code == 201
    chore_id = created.json()["id"]
    assert parent_client.delete(f"/parent/chores/{chore_id}").status_code == 204

    response = parent_client.delete(f"/parent/chores/{chore_id}/permanent")

    assert response.status_code == 204
    assert session.get(Chore, UUID(chore_id)) is None


def test_parent_can_assign_a_chore_to_part_of_the_day(parent_client: TestClient) -> None:
    response = parent_client.post(
        "/parent/chores",
        json={
            "name": "Set dinner table",
            "emoji": "🍽️",
            "points": 5,
            "recurrence_type": "daily",
            "day_part": "evening",
        },
    )

    assert response.status_code == 201
    assert response.json()["day_part"] == "evening"
    dashboard_chore = next(
        chore
        for chore in parent_client.get("/dashboard").json()["chores"]
        if chore["id"] == response.json()["id"]
    )
    assert dashboard_chore["day_part"] == "evening"


def test_chore_with_completion_history_cannot_be_permanently_deleted(
    parent_client: TestClient,
) -> None:
    chore_id = parent_client.get("/dashboard").json()["chores"][0]["id"]
    assert parent_client.post(f"/chores/{chore_id}/complete").status_code == 200
    assert parent_client.delete(f"/parent/chores/{chore_id}").status_code == 204

    response = parent_client.delete(f"/parent/chores/{chore_id}/permanent")

    assert response.status_code == 409
    assert "history" in response.json()["detail"]


def test_parent_can_adjust_points(parent_client: TestClient, session: Session) -> None:
    response = parent_client.post(
        "/parent/points", json={"amount": 25, "reason": "Helped clean garage"}
    )

    assert response.status_code == 200
    child = session.scalar(select(Child))
    assert child is not None and child.points_balance == 1275
    transaction = session.scalar(
        select(PointTransaction).where(PointTransaction.reason == "Helped clean garage")
    )
    assert transaction is not None and transaction.amount == 25


def test_parent_can_deduct_points_with_description(
    parent_client: TestClient, session: Session
) -> None:
    response = parent_client.post(
        "/parent/points",
        json={"amount": -10, "reason": "Did not do it the first time listening"},
    )

    assert response.status_code == 200
    assert response.json()["balance"] == 1240
    transaction = session.scalar(
        select(PointTransaction).where(
            PointTransaction.reason == "Did not do it the first time listening"
        )
    )
    assert transaction is not None and transaction.amount == -10
    kid_activity = parent_client.get("/dashboard").json()["point_activity"]
    deduction = next(
        item for item in kid_activity if item["reason"] == "Did not do it the first time listening"
    )
    assert deduction["amount"] == -10


def test_chore_requires_at_least_one_reward(parent_client: TestClient) -> None:
    response = parent_client.post(
        "/parent/chores",
        json={
            "name": "No reward",
            "emoji": "🫥",
            "points": 0,
            "money_reward": "0.00",
            "xoxo_reward": 0,
            "recurrence_type": "daily",
        },
    )

    assert response.status_code == 422


def test_parent_can_backfill_and_undo_historical_completion_with_audit(
    parent_client: TestClient, session: Session
) -> None:
    created = parent_client.post(
        "/parent/chores",
        json={
            "name": "Historical chore",
            "emoji": "🕰️",
            "points": 7,
            "money_reward": "0.25",
            "xoxo_reward": 2,
            "recurrence_type": "daily",
        },
    )
    assert created.status_code == 201
    chore_id = created.json()["id"]
    historical_day = (date.today() - timedelta(days=1)).isoformat()

    initial = parent_client.get(f"/days/{historical_day}")
    assert initial.status_code == 200
    historical_chore = next(item for item in initial.json()["chores"] if item["id"] == chore_id)
    assert not historical_chore["completed"]

    backfill = parent_client.put(
        f"/parent/days/{historical_day}/chores/{chore_id}",
        json={"completed": True, "reason": "Paper chart showed it was done"},
    )
    assert backfill.status_code == 200
    assert next(item for item in backfill.json()["chores"] if item["id"] == chore_id)["completed"]
    child = session.scalar(select(Child))
    assert child is not None
    assert child.points_balance == 1257
    assert child.piggy_bank_balance == Decimal("84.25")
    assert child.xoxo_balance == 2

    reopened = parent_client.put(
        f"/parent/days/{historical_day}/chores/{chore_id}",
        json={"completed": False, "reason": "Entered on the wrong day"},
    )
    assert reopened.status_code == 200
    payload = reopened.json()
    assert not next(item for item in payload["chores"] if item["id"] == chore_id)["completed"]
    assert [event["action"] for event in payload["audit"]] == ["reopened", "completed"]
    assert payload["audit"][0]["reason"] == "Entered on the wrong day"
    assert child.points_balance == 1250
    assert child.piggy_bank_balance == Decimal("84.00")
    assert child.xoxo_balance == 0
    events = list(
        session.scalars(select(ChoreAuditEvent).where(ChoreAuditEvent.chore_id == UUID(chore_id)))
    )
    assert len(events) == 2


def test_kid_cannot_edit_historical_completion(client: TestClient) -> None:
    chore_id = client.get("/dashboard").json()["chores"][0]["id"]
    historical_day = (date.today() - timedelta(days=1)).isoformat()

    response = client.put(
        f"/parent/days/{historical_day}/chores/{chore_id}",
        json={"completed": True, "reason": "Should require parent access"},
    )

    assert response.status_code == 401


def test_parent_cannot_remove_more_points_than_available(parent_client: TestClient) -> None:
    response = parent_client.post(
        "/parent/points", json={"amount": -2000, "reason": "Invalid adjustment"}
    )
    assert response.status_code == 409


def test_parent_can_adjust_piggy_bank_with_decimal_precision(
    parent_client: TestClient, session: Session
) -> None:
    response = parent_client.post(
        "/parent/piggy-bank", json={"amount": "5.25", "reason": "Weekly allowance"}
    )

    assert response.status_code == 200
    child = session.scalar(select(Child))
    assert child is not None and child.piggy_bank_balance == Decimal("89.25")
    transaction = session.scalar(
        select(PiggyBankTransaction).where(PiggyBankTransaction.reason == "Weekly allowance")
    )
    assert transaction is not None and transaction.amount == Decimal("5.25")


def test_parent_can_add_xoxos_with_a_ledger_entry(
    parent_client: TestClient, session: Session
) -> None:
    response = parent_client.post("/parent/xoxos", json={"amount": 5, "reason": "Five big hugs"})

    assert response.status_code == 200
    assert response.json()["balance"] == 5
    child = session.scalar(select(Child))
    assert child is not None and child.xoxo_balance == 5
    transaction = session.scalar(select(XoxoTransaction))
    assert transaction is not None and transaction.amount == 5


def test_parent_sets_and_applies_monthly_interest(
    parent_client: TestClient, session: Session
) -> None:
    rate = parent_client.put("/parent/piggy-bank/interest-rate", json={"annual_rate": "12.00"})
    assert rate.status_code == 200
    assert rate.json()["annual_rate"] == "12.00"

    response = parent_client.post("/parent/piggy-bank/apply-interest")

    assert response.status_code == 200
    assert response.json()["interest_earned"] == "0.84"
    assert response.json()["balance"] == "84.84"
    transaction = session.scalar(
        select(PiggyBankTransaction).where(PiggyBankTransaction.reason.like("Monthly interest%"))
    )
    assert transaction is not None and transaction.amount == Decimal("0.84")


def test_reward_request_can_be_created(client: TestClient, session: Session) -> None:
    reward_id = client.get("/dashboard").json()["rewards"][0]["id"]

    response = client.post("/reward-requests", json={"reward_id": reward_id})

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    request = session.scalar(select(RewardRequest))
    assert request is not None and request.points_cost == 100


def test_archiving_reward_preserves_request_history(
    parent_client: TestClient, session: Session
) -> None:
    reward_id = parent_client.get("/dashboard").json()["rewards"][0]["id"]
    request_id = parent_client.post("/reward-requests", json={"reward_id": reward_id}).json()["id"]

    response = parent_client.delete(f"/parent/rewards/{reward_id}")

    assert response.status_code == 204
    reward = session.get(Reward, UUID(reward_id))
    assert reward is not None and not reward.active
    assert session.get(RewardRequest, UUID(request_id)) is not None
    assert all(
        item["id"] != reward_id for item in parent_client.get("/dashboard").json()["rewards"]
    )


def test_reward_approval_deducts_points(parent_client: TestClient, session: Session) -> None:
    reward_id = parent_client.get("/dashboard").json()["rewards"][0]["id"]
    request_id = parent_client.post("/reward-requests", json={"reward_id": reward_id}).json()["id"]

    response = parent_client.patch(
        f"/parent/reward-requests/{request_id}", json={"action": "approve"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    child = session.scalar(select(Child))
    assert child is not None and child.points_balance == 1150
    transaction = session.scalar(
        select(PointTransaction).where(PointTransaction.source_type == "reward_request")
    )
    assert transaction is not None and transaction.amount == -100


def test_reward_rejection_does_not_deduct_points(
    parent_client: TestClient, session: Session
) -> None:
    reward_id = parent_client.get("/dashboard").json()["rewards"][0]["id"]
    request_id = parent_client.post("/reward-requests", json={"reward_id": reward_id}).json()["id"]

    response = parent_client.patch(
        f"/parent/reward-requests/{request_id}", json={"action": "reject"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    child = session.scalar(select(Child))
    assert child is not None and child.points_balance == 1250


def test_reward_cannot_be_approved_when_points_are_insufficient(
    parent_client: TestClient, session: Session
) -> None:
    child = session.scalar(select(Child))
    reward = session.scalar(select(Reward).where(Reward.points_cost == 500))
    assert child is not None and reward is not None
    child.points_balance = 100
    session.commit()
    request_id = parent_client.post("/reward-requests", json={"reward_id": str(reward.id)}).json()[
        "id"
    ]

    response = parent_client.patch(
        f"/parent/reward-requests/{request_id}", json={"action": "approve"}
    )

    assert response.status_code == 409
    session.refresh(child)
    assert child.points_balance == 100
    request = session.get(RewardRequest, UUID(request_id))
    assert request is not None and request.status == "pending"


def test_kid_can_request_a_skip_and_parent_can_approve_it(
    parent_client: TestClient, session: Session
) -> None:
    dashboard_before = parent_client.get("/dashboard").json()
    chore = dashboard_before["chores"][0]
    points_before = dashboard_before["points_balance"]
    money_before = dashboard_before["piggy_bank_balance"]
    xoxos_before = dashboard_before["xoxo_balance"]

    requested = parent_client.post(f"/chores/{chore['id']}/skip-requests")

    assert requested.status_code == 201
    request_id = requested.json()["id"]
    assert requested.json()["status"] == "pending"
    pending_dashboard = parent_client.get("/dashboard").json()
    pending_chore = next(item for item in pending_dashboard["chores"] if item["id"] == chore["id"])
    assert pending_chore["skip_status"] == "pending"
    assert pending_dashboard["total_count"] == dashboard_before["total_count"]
    assert parent_client.post(f"/chores/{chore['id']}/complete").status_code == 409

    overview = parent_client.get("/parent/overview").json()
    assert overview["skip_requests"][0]["id"] == request_id
    assert overview["skip_requests"][0]["status"] == "pending"

    approved = parent_client.patch(
        f"/parent/chore-skip-requests/{request_id}", json={"action": "approve"}
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    after = parent_client.get("/dashboard").json()
    skipped_chore = next(item for item in after["chores"] if item["id"] == chore["id"])
    assert skipped_chore["skip_status"] == "approved"
    assert after["total_count"] == dashboard_before["total_count"] - 1
    assert after["points_balance"] == points_before
    assert after["piggy_bank_balance"] == money_before
    assert after["xoxo_balance"] == xoxos_before
    daily = parent_client.get(f"/days/{after['date']}").json()
    skipped_day_chore = next(item for item in daily["chores"] if item["id"] == chore["id"])
    assert skipped_day_chore["skip_status"] == "approved"
    assert daily["total_count"] == after["total_count"]
    assert parent_client.post(f"/chores/{chore['id']}/complete").status_code == 409
    stored = session.get(ChoreSkipRequest, UUID(request_id))
    assert stored is not None and stored.resolved_at is not None


def test_rejected_skip_allows_completion(parent_client: TestClient) -> None:
    chore_id = parent_client.get("/dashboard").json()["chores"][0]["id"]
    request_id = parent_client.post(f"/chores/{chore_id}/skip-requests").json()["id"]

    rejected = parent_client.patch(
        f"/parent/chore-skip-requests/{request_id}", json={"action": "reject"}
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    dashboard = parent_client.get("/dashboard").json()
    chore = next(item for item in dashboard["chores"] if item["id"] == chore_id)
    assert chore["skip_status"] == "rejected"
    assert parent_client.post(f"/chores/{chore_id}/complete").status_code == 200


def test_skip_rules_prevent_duplicates_completed_requests_and_unapproved_resolution(
    client: TestClient,
) -> None:
    chore_id = client.get("/dashboard").json()["chores"][0]["id"]
    requested = client.post(f"/chores/{chore_id}/skip-requests")

    assert requested.status_code == 201
    assert client.post(f"/chores/{chore_id}/skip-requests").status_code == 409
    assert (
        client.patch(
            f"/parent/chore-skip-requests/{requested.json()['id']}",
            json={"action": "approve"},
        ).status_code
        == 401
    )


def test_completed_chore_cannot_be_requested_for_skip(client: TestClient) -> None:
    chore_id = client.get("/dashboard").json()["chores"][0]["id"]
    assert client.post(f"/chores/{chore_id}/complete").status_code == 200
    assert client.post(f"/chores/{chore_id}/skip-requests").status_code == 409


def test_recurring_chores_are_calculated_for_each_schedule() -> None:
    monday = date(2026, 8, 17)
    saturday = date(2026, 8, 22)
    base = {
        "child_id": UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Test",
        "emoji": "✅",
        "points": 1,
        "active": True,
    }
    daily = Chore(**base, recurrence_type="daily")
    weekdays = Chore(**base, recurrence_type="weekdays")
    weekends = Chore(**base, recurrence_type="weekends")
    specific = Chore(**base, recurrence_type="specific_days", recurrence_days=[0, 2])

    assert chore_occurs_on(daily, monday)
    assert chore_occurs_on(daily, saturday)
    assert chore_occurs_on(weekdays, monday)
    assert not chore_occurs_on(weekdays, saturday)
    assert not chore_occurs_on(weekends, monday)
    assert chore_occurs_on(weekends, saturday)
    assert chore_occurs_on(specific, monday)
    assert not chore_occurs_on(specific, saturday)


def test_parent_pin_protects_management_routes(client: TestClient) -> None:
    assert client.get("/parent/overview").status_code == 401
    assert client.post("/parent/login", json={"pin": "1111"}).status_code == 401

    login = client.post("/parent/login", json={"pin": "2468"})

    assert login.status_code == 204
    assert client.get("/parent/overview").status_code == 200
    client.post("/parent/logout")
    assert client.get("/parent/overview").status_code == 401


def test_parent_can_change_pin_without_storing_plaintext(
    client: TestClient, session: Session
) -> None:
    assert client.post("/parent/login", json={"pin": "2468"}).status_code == 204

    response = client.put("/parent/pin", json={"current_pin": "2468", "new_pin": "1357"})

    assert response.status_code == 204
    assert client.get("/parent/overview").status_code == 401
    assert client.post("/parent/login", json={"pin": "2468"}).status_code == 401
    assert client.post("/parent/login", json={"pin": "1357"}).status_code == 204
    stored = session.scalar(select(HouseholdSecurity))
    assert stored is not None
    assert stored.pin_hash != "1357"
    assert stored.pin_salt != "1357"


def test_completing_all_required_chores_starts_streak(client: TestClient) -> None:
    chores = client.get("/dashboard").json()["chores"]
    for chore in chores:
        assert client.post(f"/chores/{chore['id']}/complete").status_code == 200

    dashboard = client.get("/dashboard").json()

    assert dashboard["completed_count"] == dashboard["total_count"] == 4
    assert dashboard["streak_days"] == 1


def test_production_rejects_demo_parent_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            parent_pin="2468",
            session_secret="local-development-secret-change-me",
        )
