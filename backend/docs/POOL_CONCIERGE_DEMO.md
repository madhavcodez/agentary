# Pool Concierge — Demo Runbook

End-to-end runbook for the Pool Concierge vertical, covering Streams A
(mission), C (contractor pipeline), D (contracts + permits), and E
(orchestrator + Telegram + cron).

## 0. Prerequisites

- Docker + Docker Compose installed
- Python 3.13 virtualenv for the backend
- `~/.openclaw/openclaw.json` contains a Telegram bot token under
  `channels.telegram.botToken`

## 1. Start infrastructure

From the repo root:

```bash
docker compose up -d postgres redis qdrant
```

Wait until Postgres is healthy (`docker compose ps` shows `healthy`).

## 2. Apply migrations

```bash
cd backend
alembic upgrade head
```

The last two migrations you should see applied:

- `f2e9d8c7b605_contractor_reports` (Stream C)
- `f3fa0e9d8a06_pool_pipeline_runs` (Stream E)

## 3. Configure environment

Copy `.env.example` to `.env` and fill in at minimum:

```bash
POOL_CONCIERGE_ENABLED=true
POOL_CONCIERGE_DEFAULT_STATE=TX
POOL_CONCIERGE_MAX_BUDGET_USD=1200000
POOL_CONCIERGE_MIN_BUDGET_USD=500000

# Data source keys (optional for demo — connectors skip if missing)
ZILLOW_API_KEY=...
ATTOM_API_KEY=...
REGRID_API_KEY=...
MAPBOX_TOKEN=...
YELP_API_KEY=...
GOOGLE_PLACES_API_KEY=...

# DocuSign (safe default: empty = mock envelopes)
DOCUSIGN_INTEGRATION_KEY=
DOCUSIGN_USER_ID=
DOCUSIGN_ACCOUNT_ID=
DOCUSIGN_RSA_PRIVATE_KEY_B64=
DOCUSIGN_ENVIRONMENT=demo

# Auth / app secrets
JWT_SECRET_KEY=<32+ chars>
SECRET_KEY=<32+ chars>
```

## 4. Run the integration test

This covers the entire pipeline with all external services mocked — no
real HTTP traffic leaves the machine:

```bash
cd backend
pytest tests/integration/test_pool_concierge_e2e.py -v
```

Expected output:

```
tests/integration/test_pool_concierge_e2e.py::test_pool_concierge_e2e_golden_path PASSED
tests/integration/test_pool_concierge_e2e.py::test_pool_concierge_e2e_records_correct_counts PASSED
```

Run the complete Pool Concierge suite at once:

```bash
pytest tests/verticals/pool_concierge tests/services/telegram tests/integration -v
```

## 5. Start the backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger is at <http://localhost:8000/docs>.

## 6. Kick off a pipeline run manually

```bash
curl -X POST http://localhost:8000/api/verticals/pool/run \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<user-uuid>","zipcode":"75024","radius_mi":5.0}'
```

Response (202):

```json
{
  "run_id": "3fa0e9d8-...",
  "status": "pending",
  "message": "pool pipeline queued"
}
```

Poll the run:

```bash
curl http://localhost:8000/api/verticals/pool/runs/<run_id>
```

Status progression: `pending → discovering → scoring →
contractor_quoting → ready`.

Expected ready payload summary:

```json
{
  "status": "ready",
  "total_listings": 3,
  "ready_listings": 3,
  "summary": {
    "top_listings": [
      {
        "pool_listing_id": "...",
        "address": "2025 Legacy Dr, Plano, TX 75024",
        "list_price": 1100000,
        "score": 0.91,
        "contractor_status": "ready",
        "quote_count": 3,
        "permit_item_count": 7
      },
      ...
    ]
  }
}
```

## 7. Send the digest to Telegram

```bash
curl -X POST \
  http://localhost:8000/api/verticals/pool/runs/<run_id>/notify-telegram \
  -H "Content-Type: application/json" \
  -d '{"chat_id":"8412763478"}'
```

Your bot (`@edward_the_ai_bot`) will receive a Markdown message with
the top three listings and three inline buttons per row (`See quotes`,
`Draft contract`, `Pass`).

## 8. Drive the bot from Telegram

With the bot running and pool handlers registered, send:

```
/pool_search 75024
```

You should see:

1. `Starting search for pool-ready houses in 75024...`
2. (a few seconds later) the digest with three listings and buttons.

Tap `See quotes` on any listing to kick off the contractor pipeline;
the bot will send back a ranked list of BlueWave / Reef / Sunset quotes.

## 9. Register the morning cron

```bash
python ~/.openclaw/scripts/register_pool_cron.py
```

This merges (without clobbering) a new entry into
`~/.openclaw/cron/jobs.json`:

- Name: `pool_concierge_morning_digest`
- Schedule: `0 7 * * *` (07:00 CT)
- Action: POST `/api/verticals/pool/run` for every enabled
  `PoolSavedSearch`, then POST `/api/verticals/pool/runs/{id}/notify-telegram`

Re-running the script is idempotent (`jobs.json.pre-pool-concierge.bak`
is the one-shot backup).

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `run` stays on `discovering` forever | Zillow key missing | Set `ZILLOW_API_KEY` or mock via DI |
| `contractor_status: "failed"` for every listing | Yelp/Google Places keys missing | Add keys |
| Telegram send returns `ok=false` | Bot token missing | Set `AGENTARY_TELEGRAM_BOT_TOKEN` or check `~/.openclaw/openclaw.json` |
| Contract send returns `is_mock=true` | DocuSign creds missing **or** `force=false` **or** `attorney_review_status != APPROVED` | Expected in demo — all three gates must pass for real sends |
