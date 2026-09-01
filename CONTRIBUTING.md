# Contributing

Thank you for helping improve Kids Chores.

## Ground rules

- Use only synthetic household and child data in code, tests, screenshots, issues, and pull requests.
- Never commit `.env`, credentials, tokens, PINs, private URLs, residential locations, school information, or production exports.
- Keep the kid experience simple, touch-friendly, and tablet-first.
- Preserve transactional ledgers, decimal-safe money, parent authorization, and idempotent daily completion behavior.
- Discuss notification, authentication, AI, or major gamification changes before implementation.

## Development

Follow the setup instructions in [README.md](README.md). Before opening a pull request, run:

```powershell
cd backend
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy

cd ../frontend
npm test
npm run lint
npm run typecheck
npm run build
npm audit --audit-level=high
```

Also validate both Compose files from the repository root. Keep each pull request focused and explain behavioral, migration, privacy, and deployment impacts.