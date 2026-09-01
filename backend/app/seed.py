from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Child,
    Chore,
    PiggyBankTransaction,
    PointTransaction,
    Reward,
    SavingsGoal,
)


def seed_demo_data(session: Session) -> Child:
    existing = session.scalar(select(Child).order_by(Child.created_at).limit(1))
    if existing is not None:
        return existing

    child = Child(name="Kid", points_balance=1250, piggy_bank_balance=Decimal("84.00"))
    session.add(child)
    session.flush()
    session.add_all(
        [
            PointTransaction(
                child_id=child.id,
                amount=1250,
                reason="Demo starting balance",
                source_type="seed",
            ),
            PiggyBankTransaction(
                child_id=child.id,
                amount=Decimal("84.00"),
                reason="Demo starting balance",
            ),
            Chore(
                child_id=child.id,
                name="Make Bed",
                emoji="🛏️",
                points=10,
                day_part="morning",
            ),
            Chore(
                child_id=child.id,
                name="Brush Teeth",
                emoji="🪥",
                points=5,
                day_part="morning",
            ),
            Chore(
                child_id=child.id,
                name="Read 20 Minutes",
                emoji="📚",
                points=10,
                day_part="after_school",
            ),
            Chore(
                child_id=child.id,
                name="Clean Room",
                emoji="🧹",
                points=20,
                day_part="evening",
            ),
            Reward(child_id=child.id, name="30 min game time", emoji="🎮", points_cost=100),
            Reward(child_id=child.id, name="Ice cream", emoji="🍦", points_cost=150),
            Reward(child_id=child.id, name="Movie night", emoji="🎬", points_cost=200),
            Reward(
                child_id=child.id,
                name="Add $5 to piggy bank",
                emoji="💵",
                points_cost=500,
            ),
            SavingsGoal(
                child_id=child.id,
                name="LEGO Set",
                emoji="🧱",
                target_amount=Decimal("120.00"),
            ),
        ]
    )
    session.commit()
    return child


def main() -> None:
    with SessionLocal() as session:
        child = seed_demo_data(session)
        print(f"Demo data ready for {child.name} ({child.id})")


if __name__ == "__main__":
    main()
