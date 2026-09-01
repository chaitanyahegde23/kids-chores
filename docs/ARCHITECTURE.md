# Architecture

Kids Chores is a self-contained application with its own API, database, credentials, volume, and deployment boundary.

```text
Samsung tablet / phone / desktop
              |
          HTTPS + Cloudflare Access
              |
      Cloudflare outbound tunnel
              |
        Caddy web container
       /              \ /api/*
React/Vite/PWA       FastAPI service
                          |
                    SQLAlchemy 2
                          |
                     PostgreSQL 16
```

## Backend

- FastAPI exposes the kid dashboard/actions and PIN-protected parent management API.
- Thin route handlers delegate balance, completion, recurrence, streak, and reward decisions to the service layer.
- SQLAlchemy 2 models use UUID identifiers. Alembic owns schema changes.
- PostgreSQL `NUMERIC(12,2)` and Python `Decimal` represent piggy-bank and goal money.
- `Child.points_balance`, `Child.piggy_bank_balance`, and `Child.xoxo_balance` are transactionally maintained snapshots. Every change has a matching immutable ledger row, including manually applied interest and every nonzero component of a chore award.
- `UNIQUE(chore_id, child_id, completion_date)` is the final concurrency guard against duplicate chore awards.
- `chore_skip_requests` records one same-day request per chore, child, and household-local date. Pending and approved skips block completion; parent approval removes the chore from that day's required total without changing any reward balance. Rejections leave the chore available for completion.
- A chore may award any combination of nonnegative points, money, and XOXOs, but at least one component must be positive. A completion snapshots all three configured values so later chore edits do not rewrite history.
- Kids can query a household-local date read-only and undo only today's own completion. Parents can backfill or reopen a completion for any non-future date. Backfills apply the snapshotted award through the same balance and ledger transaction as a current completion; reopening and kid undo write inverse ledger rows and are rejected if any resulting balance would be negative.
- `chore_audit_events` is append-only application history for completion and reopening actions. It records the effective household date, actor, reason, and all three signed reward deltas. Existing completions are imported as system audit events during migration.
- Reward requests snapshot their point cost. Approval locks the request and child, verifies the current balance, creates the deduction ledger row, and resolves the request in one transaction.
- Chores and rewards are archived by setting them inactive, preserving completion, skip-request, and reward-request history; parent edits can reactivate them. An archived chore can be permanently deleted only when it has no completion, audit, or skip-request history.
- Household-local dates use `HOUSEHOLD_TIMEZONE`. Daily recurrence uses Python weekday numbers: Monday `0` through Sunday `6`.

## Parent protection

The four-digit PIN is compared in constant time. A successful login creates a bounded HMAC-signed, HttpOnly, SameSite=Strict cookie. Production also marks it Secure. The environment PIN is used until a parent changes it; thereafter only a salted scrypt hash is stored. Plaintext PINs and session tokens are never stored in browser JavaScript or the database.

This is intentionally small-scope authentication. Production must retain the Cloudflare Access allowlist described in the deployment runbook.

## Frontend and PWA

- React, TypeScript, and Vite render separate `/` kid and `/parent` experiences.
- Local Vite and production Caddy both expose the API as same-origin `/api`.
- The kid UI uses large touch targets, responsive two-pane tablet layout, fast completion feedback, clear states, and reduced-motion support.
- Home and School forecasts load automatically as separate cards. Labels and postal-code/city searches come from environment settings; the server resolves them through Open-Meteo and the browser receives no coordinates or location permission prompt.
- The parent UI uses conventional tabbed management forms and compact histories.
- Point deductions use an explicit add/deduct choice, a positive magnitude, and a required description; the API stores the resulting signed ledger amount.
- The kid dashboard exposes only the eight newest point-ledger rows as a read-only activity feed, including signed amounts, reasons, and timestamps; mutation endpoints remain parent-protected.
- Kid and parent history use a Sunday–Saturday summary strip with all-done, partial, empty, selected, today, and future states. Week arrows support quick browsing while a native date control retains direct date/year navigation. Kid history is read-only outside today; the parent History tab requires a reason for every backfill or reopening and displays the daily audit trail.
- Each chore carries a parent-configured day part so the kid mission is grouped into Morning, After School, and Evening. The selected week summary drives a compact personal recap; no sibling comparison is introduced.
- Joke of the Day is selected deterministically from a source-controlled kid-safe set using the household date, so it requires no external request or tracking.
- The web manifest, maskable SVG icon placeholders, standalone display mode, and service worker support home-screen installation. API data is never cached by the service worker.

## Persistence and seeding

The API container applies `alembic upgrade head` and runs the idempotent seed command before starting. An existing child prevents demo records from being inserted again.

## Testing

- Backend tests use a foreign-key-enabled isolated SQLite database for fast service/API verification; the migration is separately exercised against PostgreSQL in Docker.
- Frontend tests use Vitest, Testing Library, and mocked same-origin HTTP responses.
- Final gates cover tests, Ruff, formatting, mypy, ESLint, TypeScript, Vite production build, npm audit, Compose parsing, PostgreSQL migration, and container health.
