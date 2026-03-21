# Agentary

**Autonomous AI Research & Intelligence Platform**

Deploy expert AI agent crews that research any domain, make voice calls, analyze data, and generate polished reports — automatically.

## What It Does

Agentary assembles teams of specialized AI agents to execute research missions. You define what you want to know, and the platform:

1. **Selects experts** — Gemini auto-picks the best agents for your mission (Web Researcher, Market Analyst, Data Analyst, Property Researcher, Local Scout, Voice Caller)
2. **Plans tasks** — AI generates a research plan with parallel and sequential phases
3. **Executes research** — Agents run simultaneously, using tools (web search, neural search, web scraping, data analysis, voice calls, chart generation)
4. **Synthesizes findings** — A Synthesizer agent resolves contradictions, identifies gaps, and ranks insights
5. **Writes reports** — A Report Writer generates structured documents with charts, citations, and executive summaries
6. **Delivers results** — Real-time activity feed, exportable findings (CSV/JSON/Excel), and shareable PDF reports

## Architecture

```
+-----------------------------------------------------------------+
|                    Next.js Dashboard (Port 3000)                |
|  Home | Projects | Missions | Workflows | Voice | Reports      |
+-----------------------------------------------------------------+
|                   FastAPI Backend (Port 8000)                   |
|  34 API Routes | JWT Auth | WebSocket Live Feed | CircuitBreak |
+----------+----------+----------+----------+--------------------+
| Crew     | Research | Voice    | Workflow | Report             |
| Runner   | Engine   | Pipeline | Engine   | Generator          |
+----------+----------+----------+----------+--------------------+
|              Gemini 2.5 Flash (LLM + Tool Calling)             |
+----------+----------+----------+----------+--------------------+
|PostgreSQL|  Redis   |  Qdrant  |  Celery  | APScheduler        |
| (Data)   | (Cache)  | (Vector) | (Queue)  | (Cron)             |
+----------+----------+----------+----------+--------------------+
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, ReactFlow |
| **Backend** | FastAPI, SQLAlchemy, Pydantic, Python 3.13 |
| **AI/LLM** | Google Gemini 2.5 Flash (tool-calling, structured output, embeddings) |
| **Voice** | Pipecat + Gemini Live + Twilio (outbound calling) |
| **Search** | Exa API (neural search), Gemini grounding |
| **Database** | PostgreSQL 16, Redis 7, Qdrant (vector) |
| **Task Queue** | Celery + Redis broker (with inline fallback) |
| **Infrastructure** | Docker Compose (8 services), Nginx reverse proxy |

## Expert Agents

| Agent | Specialty | Tools |
|-------|-----------|-------|
| Web Researcher | Systematic web research with source citation | gemini_search, exa_search, web_scraper |
| Data Analyst | Statistical analysis and data visualization | python_executor, chart_generator |
| Market Analyst | Market sizing, competitive analysis, SWOT | gemini_search, exa_search, web_scraper, python_executor |
| Property Researcher | Real estate data, comps, market trends | gemini_search, exa_search, web_scraper |
| Local Scout | Local business intelligence, area profiles | gemini_search, exa_search, web_scraper, voice_caller |
| Voice Caller | Phone-based data extraction | voice_caller |
| Synthesizer | Cross-reference findings, resolve contradictions | (LLM only) |
| Report Writer | Generate polished reports with charts | chart_generator |

## Tools

- **gemini_search** — Broad web search using Gemini's grounding
- **exa_search** — Neural/semantic search via Exa API
- **web_scraper** — Full-page scraping with BeautifulSoup (text, tables, links)
- **python_executor** — Sandboxed Python execution for data analysis
- **voice_caller** — Outbound voice calls via Twilio + Pipecat
- **chart_generator** — Chart.js config generation (line, bar, pie, scatter, radar)

## Mission Execution Flow

```
User creates mission
        |
        v
Gemini selects best experts (3-5 agents)
        |
        v
Gemini plans research tasks
        |
        +-- PARALLEL PHASE --------------------------------+
        |   Web Researcher: 2-3 search tasks               |
        |   Market Analyst: trend + entity tasks            |
        |   Data Analyst: analysis tasks                    |
        |   (each agent uses agentic tool-calling           |
        |    loop: up to 6 iterations with Gemini)          |
        +--------------------------------------------------+
        |
        v  All findings collected
        |
        +-- SYNTHESIS PHASE
        |   Synthesizer: de-duplicate, cross-reference,
        |   identify gaps, rank insights
        |
        +-- REPORT PHASE
        |   Report Writer: executive summary, sections,
        |   charts, citations, methodology
        |
        v
Mission complete -- findings + report available
```

## Pages

| Route | Purpose |
|-------|---------|
| `/` | Project creation wizard with 6 research templates |
| `/projects` | Project list with type badges and stats |
| `/projects/[id]` | Project detail: missions, findings, stats |
| `/missions` | All missions with status filters |
| `/missions/[id]` | Live mission detail: activity feed, findings, structured data |
| `/dashboard` | Command center: live events, active missions, monitors |
| `/workflows` | Visual workflow editor (ReactFlow) |
| `/workflows/[id]` | Workflow DAG editor with node palette |
| `/reports` | Report list with PDF export and sharing |
| `/reports/[id]` | Full report viewer with TOC and charts |
| `/monitors` | Automated change detection monitors |
| `/voice` | Voice extraction campaigns |
| `/analytics` | Platform-wide statistics |
| `/settings` | Infrastructure health and integration status |

## Data Model

**Core:** Project > Mission > CrewRun > CrewTask > Finding

**36 models** including: User, Project, Mission, AgentCrew, ExpertAgent, CrewTask, Finding, Report, Workflow, WorkflowRun, WorkflowTemplate, Monitor, Alert, VoiceExtraction, CallRecord, Entity, DataSource, KnowledgeBase, and more.

## Setup

### Prerequisites
- Python 3.13+, Node.js 18+, Docker

### Quick Start

```bash
# 1. Clone
git clone https://github.com/madhavcodez/agentary.git
cd agentary

# 2. Start infrastructure
docker compose up -d db redis qdrant

# 3. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # Add your GEMINI_API_KEY
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Frontend (new terminal)
cd dashboard
npm install
npm run dev

# 5. Open http://localhost:3000
```

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `DATABASE_URL` | No | PostgreSQL (default: localhost) |
| `REDIS_URL` | No | Redis (default: localhost) |
| `EXA_API_KEY` | No | Exa neural search |
| `TWILIO_*` | No | Voice calling (SID, token, number) |
| `RESEND_API_KEY` | No | Email alerts |

## Development

```bash
# Run backend tests (552 passing)
cd backend && .venv/bin/python -m pytest tests/ -q

# Build frontend
cd dashboard && npm run build

# Full Docker deployment
docker compose up --build
```

## Project Structure

```
agentary/
+-- backend/
|   +-- app/
|   |   +-- api/              # 34 FastAPI routers
|   |   +-- models/           # 36 SQLAlchemy models
|   |   +-- services/
|   |   |   +-- crews/        # CrewRunner, tools, events, expert registry
|   |   |   +-- research/     # Research engine
|   |   |   +-- reports/      # Report generator, PDF export, charts
|   |   |   +-- workflow/     # Workflow executor
|   |   |   +-- voice/        # Voice pipeline (Pipecat + Twilio)
|   |   |   +-- data_sources/ # 10 data connectors
|   |   +-- core/             # WebSocket manager, Redis bridge
|   |   +-- tasks/            # Celery background tasks
|   +-- tests/                # 556 tests
+-- dashboard/
|   +-- app/                  # 21 Next.js pages
|   +-- components/           # 23 React components
|   +-- lib/                  # API client, types, hooks, auth
+-- docker-compose.yml        # 8-service orchestration
+-- nginx.conf                # Reverse proxy routing
```

## License

MIT
