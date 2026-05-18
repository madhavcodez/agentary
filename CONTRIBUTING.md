# Contributing to Agentary

Thanks for the interest. This guide is short on purpose — read it, then ship.

## Local setup

```bash
git clone https://github.com/madhavcodez/agentary.git
cd agentary
cp .env.example .env
# Fill in the keys you need (GEMINI_API_KEY at minimum)

docker compose up -d db redis qdrant
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# In another shell:
cd dashboard && npm install && npm run dev
```

Dashboard: http://localhost:3000 · API docs: http://localhost:8000/docs

## Branch & commit

- Branch off `main`. Use a descriptive prefix:
  - `feat/<scope>` — new capability
  - `fix/<scope>` — bug fix
  - `refactor/<scope>` — no behavior change
  - `chore/<scope>` — tooling, docs
  - `perf/<scope>` — performance
  - `security/<scope>` — security fix
- Commit messages use [Conventional Commits](https://www.conventionalcommits.org/): `<type>: <description>`
- One logical change per PR. Big refactors land as a sequence of small reviewable PRs.

## Quality bar

Before opening a PR:

```bash
# Backend
cd backend
ruff check app tests
black --check app tests
isort --check-only app tests
pytest -q

# Dashboard
cd dashboard
npm run lint
npx tsc --noEmit
npm test
npm run build
```

CI runs all of these on every PR. PRs that fail CI are not reviewed.

## Code rules

These come from `~/.claude/rules/` and apply uniformly:

- Files under 800 lines, functions under 50 lines
- No deep nesting (>4 levels) — use early returns
- Type hints on all Python function signatures
- TypeScript `strict` mode on
- No `console.log`, `print()`, or other debug leftovers
- No hardcoded secrets — read from `os.environ` / `process.env`
- ORM only; never raw SQL with f-strings
- All new endpoints have `user_id` ownership scoping
- All new webhooks verify signatures / HMAC
- Routers must not call `db.query` directly — go through services

## Tests

- Minimum 80% coverage on changed code
- Test-driven for new features: write the failing test first
- AAA structure: Arrange → Act → Assert
- Descriptive names: `test_returns_empty_when_no_matches`, not `test_1`

## Migrations

- One head only. `alembic heads | wc -l` must equal 1.
- Naming: `alembic revision --autogenerate -m "short description"`
- Upgrade must be safe to retry. Downgrade must work.
- No `NOT NULL` on populated columns without a backfill step.
- Long migrations land separately from code changes.

## Security

- Never commit `.env`, credentials, or fixtures with real PII.
- Don't disable signature verification on webhooks "temporarily".
- Don't add `try: ... except: pass` to silence errors. If you must catch broadly, log with `exc_info=True`.

Report security issues privately via [GitHub Security Advisories](https://github.com/madhavcodez/agentary/security/advisories/new) — see [SECURITY.md](SECURITY.md).

## PR review

PRs are reviewed against:
- The checklist in `.github/PULL_REQUEST_TEMPLATE.md`
- CI green
- Coverage non-regressing
- Documentation updated if behavior changed

Tag `@madhavcodez` for review. Expect a response within 48 hours on weekdays.

## Architecture decisions

Significant decisions (new dependency, new module, breaking schema change) land as an ADR in `docs/adr/`. Format:

```
docs/adr/NNNN-short-title.md
```

See existing ADRs for the format.
