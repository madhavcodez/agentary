<!-- Thanks for contributing to Agentary! -->

## Summary

<!-- What does this PR change and why? Link issues with "Closes #N". -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor (no behavior change)
- [ ] Performance
- [ ] Security
- [ ] Docs / chore
- [ ] Breaking change

## Scope

- [ ] Backend
- [ ] Dashboard
- [ ] Infra / Docker / CI
- [ ] Migrations (`backend/alembic/versions/`)

## How was this tested?

<!-- Describe the test approach. Include commands and observed output. -->

- [ ] `pytest` passes locally
- [ ] `npm test` passes locally
- [ ] `npm run build` succeeds
- [ ] Manual smoke test (describe steps)

## Migration safety (if applicable)

- [ ] Upgrade is idempotent / safe to retry
- [ ] Downgrade is implemented and tested
- [ ] No table renames during normal traffic without backfill plan
- [ ] No `NOT NULL` adds on populated tables without backfill

## Security checklist

- [ ] No secrets, tokens, or PII in code, logs, or fixtures
- [ ] User input validated at the boundary
- [ ] No SQL string concatenation; ORM or parameterized queries only
- [ ] New endpoints have ownership checks (`user_id` scoping)
- [ ] New webhooks verify signatures / HMAC

## Screenshots / output

<!-- Drop UI screenshots, logs, or example responses here. -->
