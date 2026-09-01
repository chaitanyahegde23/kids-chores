# Kids Chores

[![CI](https://github.com/chaitanyahegde23/kids-chores/actions/workflows/ci.yml/badge.svg)](https://github.com/chaitanyahegde23/kids-chores/actions/workflows/ci.yml)

Kids Chores is a self-hosted, tablet-first household chores and rewards dashboard. A child can complete today’s chores, see points, XOXOs, piggy-bank money and local weather, request rewards, follow a savings goal, and build a streak. Parents manage the same data behind a changeable four-digit PIN.

The application is self-contained and uses its own database, volume, credentials, and ports.

## Included MVP

- Kid dashboard at `/`
- Parent dashboard at `/parent`
- Daily, weekday, weekend, and selected-weekday chores
- Atomic, one-per-day chore completion with configurable point, money, and XOXO awards, plus same-day kid undo with matching reversal ledgers
- Sunday–Saturday kid history with completion indicators, week navigation, date/year jump, and parent backfill/correction with immutable audit events
- Parent-configured Morning, After School, and Evening chore sections
- Weekly personal-progress recap and a deterministic kid-safe Joke of the Day
- Point, XOXO, and piggy-bank transaction histories
- Kid-visible recent point activity with signed changes, descriptions, and dates
- Quick-add balances plus explicit, described point deductions
- Adjustable piggy-bank interest with explicit monthly ledger entries
- Automatic, separate Home and School weather using environment-configured location searches
- Pending reward requests with parent approval/rejection
- Same-day kid chore-skip requests with parent approval/rejection; approved skips remain visible in history and do not count as required chores
- Non-destructive chore and reward archival, plus permanent deletion for unused archived chores
- Decimal-safe savings goal and progress
- Required-chore streak
- PostgreSQL persistence and Alembic migration
- Responsive phone/tablet/desktop interface
- Installable PWA metadata, icons, and service worker
- Idempotent synthetic demo seed
- Automated backend and frontend tests

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16
- React 19, TypeScript, Vite
- Docker Compose and Caddy
- Pytest, Ruff, mypy, Vitest, Testing Library, ESLint

## Quick start with Docker

Prerequisites: Docker Desktop with Docker Compose.

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace the PostgreSQL password and session secret placeholders. For local demo use, `PARENT_PIN=2468` may remain unchanged.

```powershell
docker compose up --build
```

Open:

- Kid dashboard: `http://localhost:8081`
- Parent dashboard: `http://localhost:8081/parent`
- API docs: `http://localhost:8010/docs`
- API health: `http://localhost:8010/health`

The first start applies the migration and inserts demo data once.

Stop without deleting data:

```powershell
docker compose down
```

`docker compose down --volumes` permanently removes the local chores database.

## Run in development mode

Start PostgreSQL and the API:

```powershell
docker compose up -d db api
```

Then start Vite in another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5174`. Vite proxies `/api` to `http://localhost:8010`.

To run the API directly, use Python 3.12:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload --port 8010
```

Start only PostgreSQL with `docker compose up -d db` before applying migrations locally.

## Demo data and parent PIN

The demo seed creates:

- Kid with `1,250` points and `$84.00`
- 🛏️ Make Bed, 🪥 Brush Teeth, 📚 Read 20 Minutes, and 🧹 Clean Room
- 🎮 game time, 🍦 ice cream, 🎬 movie night, and 💵 piggy-bank rewards
- 🧱 LEGO Set goal at `$120.00`

Default local parent PIN: `2468`

Change it by setting `PARENT_PIN` in `.env` and restarting the API. Production startup requires an explicit PIN and a strong `SESSION_SECRET`.

## Validation commands

Backend, from `backend/` with the virtual environment installed:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\mypy.exe app tests
python -m alembic upgrade head
```

Frontend, from `frontend/`:

```powershell
npm ci
npm test
npm run lint
npm run typecheck
npm run build
npm audit --audit-level=high
```

Compose, from the project root:

```powershell
docker compose config --quiet
docker compose -f compose.production.yaml config --quiet
docker compose up -d --build
Invoke-RestMethod http://localhost:8081/api/health
```

## Samsung tablet installation

After production is available over HTTPS, open your configured `ALLOWED_ORIGIN` in Chrome on the Samsung tablet, open the browser menu, and choose **Add to Home screen**. The installed shortcut launches in standalone mode. Both portrait and landscape layouts are supported.

## Environment variables

| Variable | Purpose |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Isolated PostgreSQL credentials |
| `DATABASE_URL` | Direct host-side SQLAlchemy connection URL |
| `HOUSEHOLD_TIMEZONE` | Defines today, recurrence, and streak boundaries |
| `WEATHER_HOME_LABEL`, `WEATHER_HOME_LOCATION` | Home forecast label and postal code or city search |
| `WEATHER_SCHOOL_LABEL`, `WEATHER_SCHOOL_LOCATION` | School forecast label and postal code or city search |
| `PARENT_PIN` | Four-digit parent PIN |
| `SESSION_SECRET` | Signs bounded parent session cookies; minimum 24 characters |
| `PARENT_SESSION_SECONDS` | Parent session lifetime, default 12 hours |
| `ALLOWED_ORIGIN` | Browser origin permitted by CORS; set the exact HTTPS origin in production |
| `CLOUDFLARE_TUNNEL_TOKEN` | Production chores tunnel token only |

See [architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md), [engagement backlog](docs/BACKLOG.md), and the exact [deployment runbook](docs/DEPLOYMENT.md).

## Security and privacy

- Keep all real credentials and household-specific settings in the ignored `.env`; commit only placeholder examples.
- Never publish a Cloudflare tunnel token, database password, parent PIN, session secret, household email, home address, school, or child data.
- Use synthetic data in issues, screenshots, tests, and pull requests.
- Report vulnerabilities privately using the process in [SECURITY.md](SECURITY.md).

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Kids Chores is available under the [MIT License](LICENSE).

## Current limitations

- The UI operates on one seeded child; the schema is child-scoped for later expansion.
- A changed historical chore schedule is not versioned, so streak history uses the current schedule.
- Historical dates show the current chore schedule plus any completion actually recorded on that date; schedule edits are not retroactively versioned.
- Archived chores and rewards remain visible in parent management and can be reactivated by editing them.
- A four-digit PIN must remain behind Cloudflare Access in production.
- PWA shell assets can load offline, but chore data and actions require the home server.
- Email and push notifications, AI, native Android code, and additional gamification are intentionally excluded pending a dedicated secure notification design.
