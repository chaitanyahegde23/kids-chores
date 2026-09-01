# Kids Chores roadmap

The first MVP is complete and production-ready. Status reflects the implementation available in this repository.

| ID | Milestone | Outcome | Status |
|---|---|---|---|
| CHORES-001 | App foundation | Isolated FastAPI/React application, environment configuration, Docker development stack | Complete |
| CHORES-002 | Database models | PostgreSQL schema, Alembic migration, child-scoped entities, immutable ledgers, idempotent seed | Complete |
| CHORES-003 | Kid dashboard | Greeting, balances, touch-friendly chores, rewards, goal, and streak | Complete |
| CHORES-004 | Chore completion + points ledger | Household-date recurrence, one award per chore/day, atomic point history | Complete |
| CHORES-005 | Parent dashboard | Four-digit PIN session, overview, chore CRUD, responsive management navigation | Complete |
| CHORES-006 | Piggy bank | Decimal-safe parent adjustments and transaction history | Complete |
| CHORES-007 | Rewards | Reward CRUD, pending requests, atomic approval/rejection, insufficient-balance protection | Complete |
| CHORES-008 | Savings goal + streak | Parent-managed goal, progress, and completed-required-chore streak | Complete |
| CHORES-009 | PWA / tablet optimization | Manifest, icon placeholders, service worker, standalone mode, responsive touch UI | Complete |
| CHORES-010 | Tests and polish | Business-flow API tests, UI tests, lint/type/build/audit gates, accessible states | Complete |
| CHORES-011 | Production deployment | Production Compose, Caddy same-origin proxy, isolated ports/volumes, Cloudflare Tunnel and Access boundary | Complete |
| CHORES-012 | History retention | Non-destructive chore and reward archival preserves completions, requests, and ledger context | Complete |
| CHORES-013 | Family dashboard expansion | Chore-create fix, safe delete, XOXOs, weather, bank interest, PIN changes, and expanded Access allowlist | Complete |
| CHORES-014 | Flexible chore awards | Chores award any combination of points, money, and XOXOs; parent point deductions require an explicit action and description | Complete |
| CHORES-015 | Reward-request email | Secure outbound notification and parent review links with replay-safe approval confirmation | Proposed |
| CHORES-016 | Historical chore records | Kid calendar history, parent backfill/reopen controls, reversing ledgers, and immutable daily audit trail | Complete |
| CHORES-017 | Weekly history navigator | Sunday–Saturday completion strip, week paging, direct date/year jump, and responsive tablet states | Complete |
| CHORES-018 | Configured family weather | Automatic, separate Home and School forecasts with environment-driven labels and locations | Complete |
| CHORES-019 | My Day journey | Parent-configured Morning, After School, and Evening chore sections | Complete |
| CHORES-020 | Weekly story card | Personal weekly completion recap without comparison or leaderboards | Complete |
| CHORES-021 | Joke of the Day | Deterministic daily kid-safe one-line joke | Complete |
| CHORES-033 | Kid-visible points activity | Recent point additions and deductions show signed amounts, descriptions, and dates on the kid profile | Complete |
| CHORES-034 | Same-day kid chore undo | Completed chores expose Undo today and reverse every awarded currency through immutable ledgers | Complete |
| CHORES-035 | Parent-approved chore skips | Same-day kid requests, parent approval/rejection, completion conflict protection, and historical skip status | Complete |

The prioritized engagement pipeline is maintained in the [engagement backlog](BACKLOG.md).

## Deliberate MVP boundaries

- The UI selects the first configured child. Every domain row still carries `child_id` for a future child selector.
- The four-digit PIN is appropriate only behind the documented Cloudflare Access boundary. It is not standalone internet-grade authentication.
- Chore edits apply to future streak calculation because schedule-version history is not stored yet.
- Historical schedule display uses the current recurrence definition plus recorded completions; versioned chore definitions remain a future enhancement.
- Archived chores and rewards retain their operational history and can be reactivated from parent management; unused archived chores may be permanently deleted.
- No email or push notifications, AI features, native Android client, or additional game mechanics are included yet.
