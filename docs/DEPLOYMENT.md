# Production deployment

This application uses its own Compose project, containers, PostgreSQL volume, database credentials, Caddy loopback port `8081`, and optional Cloudflare tunnel token. Do not reuse credentials or storage from another application.

## 1. Prepare production secrets

For a new deployment, select the Docker connector command in the Cloudflare tunnel setup page and copy it to the clipboard. Then run:

```powershell
.\scripts\initialize-production.ps1 -AllowedOrigin https://chores.example.com
```

The script extracts the tunnel token without printing it and creates an ignored `.env` with unique database, session, and parent credentials. It refuses to overwrite an existing `.env` unless `-Force` is explicitly supplied.

Alternatively, copy `.env.example` to `.env`, then set:

```text
POSTGRES_PASSWORD=<unique URL-safe random value of at least 32 characters>
PARENT_PIN=<a non-demo four-digit PIN>
SESSION_SECRET=<at least 32 cryptographically random characters>
HOUSEHOLD_TIMEZONE=America/New_York
ALLOWED_ORIGIN=https://chores.example.com
CLOUDFLARE_TUNNEL_TOKEN=<token for the new Kids Chores tunnel>
```

Generate a session secret in PowerShell without printing other environment values:

```powershell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
[Convert]::ToBase64String($bytes)
```

Store the result only in ignored `.env`. Do not commit or paste it into an issue.

If the PostgreSQL volume already exists and `POSTGRES_PASSWORD` changes, synchronize the existing database role before restarting the API:

```powershell
.\scripts\rotate-postgres-password.ps1
```

This updates only the application database role and does not print the password.

## 2. Validate and start the private core

From the Kids Chores project root:

```powershell
docker compose -f compose.production.yaml config --quiet
docker compose -f compose.production.yaml build api web
docker compose -f compose.production.yaml up -d db api web
docker compose -f compose.production.yaml ps
Invoke-RestMethod http://127.0.0.1:8081/healthz
Invoke-RestMethod http://127.0.0.1:8081/api/health
```

Expected responses are `ok` and `{"status":"ok"}`. Production API documentation is disabled.

## 3. Create the Cloudflare boundary

1. In Cloudflare Zero Trust, create a new remotely managed tunnel named `kids-chores`.
2. Copy only its token into this app’s ignored `.env`.
3. Add a published application route:
   - Hostname: `chores.example.com`
   - Service: `HTTP`
   - URL: `web:8080`
4. Create a separate Access application for `chores.example.com`.
5. Attach the household Access policy (currently `Household Access Policy`), which allows only approved identities and otherwise denies access by default.
6. Do not publish residential IP DNS records or forward router ports.

Then start the connector:

```powershell
docker compose -f compose.production.yaml --profile tunnel up -d tunnel
docker compose -f compose.production.yaml --profile tunnel ps
```

s’s web service.

## 4. Acceptance checks

1. Open `https://chores.example.com` over cellular data and confirm Cloudflare Access denies an unapproved identity.
2. Sign in with an allowed household identity and verify the kid dashboard.
3. Complete a synthetic chore configured with points, money, and XOXOs once; verify all configured ledgers, then confirm a second completion remains blocked.
4. Open `/parent`, verify an incorrect PIN is rejected, then use the configured PIN and test a PIN change.
5. Create, archive, and delete an unused chore; verify a chore with completion history remains archive-only.
6. Add and deduct points with descriptions, adjust money, XOXOs, and the interest rate; apply one month of interest and verify each balance change has a history entry.
7. Verify the Home and School forecasts match the configured locations without a tablet location prompt, then request a reward in kid mode and approve it in parent mode.
8. On the Samsung tablet, use Chrome’s **Add to Home screen** action and verify standalone launch in portrait and landscape.
9. Confirm `https://chores.example.com/api/openapi.json` returns 404.
10. Browse previous/next weeks in kid mode, select a day from the seven-day strip, jump to a previous year/date, and verify history is read-only. In Parent → History, backfill a synthetic completion with a reason, verify its balances and audit event, then undo it and verify reversing ledger entries.
11. Confirm the kid dashboard shows one Joke of the Day, a weekly recap, and Morning, After School, and Evening chore groups. In Parent → Chores, create or edit a synthetic chore and verify its part of day is preserved.
12. Add and deduct synthetic points with distinct descriptions, then verify the newest signed changes, descriptions, and dates appear read-only in the kid Points activity card.
13. Complete a synthetic multi-currency chore in kid mode, tap Undo, and verify the completion, balances, weekly progress, point activity, and all reversal ledgers update. Confirm historical chores remain read-only and an undo that would make any balance negative is rejected.
14. Request a same-day chore skip in kid mode. Confirm the chore cannot be completed while pending, approve it in Parent → Rewards, verify it no longer counts as required and no balance changes, then verify the skipped status remains visible in daily history. Repeat with rejection and confirm completion becomes available.

## Operations and backup

- Start Docker Desktop at sign-in and keep the host powered and patched.
- Monitor with `docker compose -f compose.production.yaml --profile tunnel ps` and `logs --tail 100`.
- Back up PostgreSQL using `pg_dump`; do not copy a live Docker volume.
- Test restoration with synthetic data before relying on backups.
- Stop safely with `docker compose -f compose.production.yaml --profile tunnel down`. Never add `--volumes` unless intentionally deleting all chores data.
