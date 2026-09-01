# Kids Chores engineering guide

- Keep the kid experience extremely simple, touch-friendly, and tablet-first.
- Keep FastAPI handlers thin and business mutations transactional in services.
- Maintain point and piggy-bank ledgers; never mutate a displayed balance without a matching ledger row.
- Use `Decimal` and PostgreSQL `NUMERIC` for money, never floating-point storage.
- Every chore completion must be idempotent per chore, child, and household-local date.
- Parent mutations require the parent session. Do not expose or log the PIN or session secret.
- Keep child ownership on domain entities even while the UI supports one child.
- Use only synthetic demo data in source control.
- Run backend tests, Ruff, formatting, mypy, frontend tests, lint, typecheck, build, and audit before delivery.
- Do not add AI, notifications, complex authentication, or additional gamification without explicit approval.
