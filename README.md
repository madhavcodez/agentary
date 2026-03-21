# Agentary

Autonomous research & intelligence platform. Deploy crews of specialized AI agents to gather findings, make voice calls, and generate reports.

## Quick Start

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys (GEMINI_API_KEY, TWILIO_*, EXA_API_KEY)

# Start everything
docker compose up -d

# Run migrations
docker compose exec backend alembic upgrade head

# Seed default data (expert agents, workflows, sources)
docker compose exec backend python -m scripts.seed

# Open dashboard
open http://localhost
```

## Architecture

| Service | Port | Description |
|---------|------|-------------|
| Dashboard | 3000 | Next.js 14 frontend |
| Backend | 8000 | FastAPI REST API |
| Celery Worker | — | Async task execution |
| Celery Beat | — | Scheduled tasks |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache, queues, pub/sub |
| Qdrant | 6333 | Vector embeddings |
| Nginx | 80 | Reverse proxy |

## Key Concepts

- **Projects** — Container for a research initiative (e.g., "Austin Real Estate Market")
- **Missions** — Specific research goals within a project
- **Expert Agents** — Specialized AI agents (WebResearcher, VoiceCaller, MarketAnalyst, etc.)
- **Findings** — Individual discovered facts or data points
- **Reports** — Generated narrative documents from findings
- **Voice Extractions** — Phone call campaigns for data collection
- **Workflows** — Reusable research pipelines (node graph)
- **Monitors** — Ongoing watches with alert rules

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Celery, PostgreSQL, Redis, Qdrant
- **Frontend**: Next.js 14, React 18, Tailwind CSS
- **Voice**: Pipecat + Gemini Live + Twilio
- **LLM**: Google Gemini 2.5 Flash
- **Search**: Exa API, Google Search

## Development

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd dashboard && npm install && npm run dev

# Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Run tests
cd backend && pytest
```

## License

MIT
