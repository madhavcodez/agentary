# Agentary

A full-stack platform I built for running autonomous research missions. Give it
an objective — say, *"map the EV charging competitive landscape"* — and it plans
the work, gathers data from multiple sources in parallel, checks its own coverage
gaps, and produces a structured, cited report. Progress streams to a live
dashboard as it runs.

It's useful for market intelligence, competitor monitoring, due diligence, lead
research, and local business data collection.

## What it does

- Breaks a research objective into tasks handled by specialized agents
- Collects in parallel — web search, page scraping, Python analysis, and
  (optionally) outbound voice calls
- Scores each finding and tracks the source it came from
- Synthesizes findings into signals, insights, and recommendations
- Exports reports as Markdown, HTML, or PDF with per-section citations

## How it works

Each mission runs through a multi-phase pipeline (inspired by
[DeerFlow](https://github.com/bytedance/deer-flow)):

1. **Scout** — one agent surveys the topic and maps the dimensions worth
   investigating.
2. **Parallel research** — multiple expert agents investigate those dimensions at
   once, each running a Gemini tool-calling loop over web search, scraping,
   Python, and charting tools.
3. **Gap check** — a synthesizer audits coverage and flags under-researched areas.
4. **Synthesis** — findings are merged, contradictions resolved, and claims
   weighted by confidence.
5. **Report** — a structured, cited report is generated and exported.

An optional pre-writing stage based on Stanford's
[STORM](https://github.com/stanford-oval/storm) plans the report outline up front
and binds each section to the evidence that supports it. It's off by default
(`AGENTARY_STORM_ENABLED`).

## Tech stack

- **Frontend** — Next.js 14 (App Router), TypeScript, Tailwind; live updates over WebSocket
- **Backend** — FastAPI + Pydantic v2
- **Async execution** — Celery + Beat scheduler (Redis broker)
- **Data** — PostgreSQL (SQLAlchemy + Alembic), Redis, and Qdrant for vector search
- **AI** — Gemini 2.5 Flash + Pro, with Exa neural search for grounding
- **Integrations** — Twilio (voice), Resend (email)

## Quick start

**Prerequisites:** Python 3.13+, Node.js 18+, Docker.

```bash
git clone https://github.com/madhavcodez/agentary.git
cd agentary

# 1. Infrastructure
docker compose up -d db redis qdrant

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8000 --reload

# 3. Celery workers (new terminal)
celery -A app.celery_app worker --loglevel=info \
  --queues=research,missions,voice,monitors,reports,workflows
celery -A app.celery_app beat --loglevel=info

# 4. Frontend (new terminal)
cd ../dashboard
npm install
npm run dev
```

Dashboard: http://localhost:3000 · API docs: http://localhost:8000/docs

## Environment variables

| Variable | Required | Purpose |
|---|:---:|---|
| `GEMINI_API_KEY` | Yes | Core LLM (reasoning, tool-calling, synthesis) |
| `DATABASE_URL` | Yes | PostgreSQL connection |
| `REDIS_URL` | Yes | Celery broker + pub/sub |
| `QDRANT_URL` | Yes | Vector search |
| `EXA_API_KEY` | No | Exa neural web search |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` | No | Outbound voice calls |
| `RESEND_API_KEY` | No | Email delivery |
| `AGENTARY_STORM_ENABLED` | No | Enable STORM pre-writing (default: `false`) |

## Project structure

```
agentary/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Crews, STORM, research, intelligence, reports, voice
│   │   ├── tasks/        # Celery tasks
│   │   ├── core/         # Logging, events, rate limits, WebSocket
│   │   ├── prompts/      # Expert-agent system prompts
│   │   └── providers/    # LLM provider integrations
│   ├── alembic/          # Migrations
│   └── tests/            # pytest suite
├── dashboard/            # Next.js 14 frontend
├── docker-compose.yml
└── nginx.conf
```

## License

MIT — built by [Madhav Chauhan](https://github.com/madhavcodez).
