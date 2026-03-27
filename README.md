<div align="center">

# AGENTARY

### Autonomous AI Research & Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Deploy expert AI agent crews that research any domain, call businesses, analyze data, and generate high-quality reports automatically.**

[Quick Start](#quick-start) · [Product Tour](#product-tour) · [Feature Catalog](#feature-catalog) · [Architecture](#architecture) · [API](#api-highlights)

</div>

---

## Product Tour

### Screenshots

<p align="center">
  <img src="docs/screenshots/home.png" alt="Agentary - Home and Mission Setup" width="100%" />
</p>

<p align="center">
  <strong>Mission Pipeline</strong><br/>
  Create and launch research missions with expert crews, then monitor execution from the live command interface.
</p>

> More screenshots will be added as additional UI captures are exported.

---

## Feature Catalog

### Why It Feels Powerful

- One mission can coordinate multiple expert agents in parallel
- Every finding includes confidence, source context, and traceable lineage
- You get both live operations visibility and polished final deliverables
- The platform supports recurring monitoring, workflows, and human-in-the-loop approvals

### Mission Execution

- Autonomous mission planning via expert crew selection
- Multi-phase run orchestration (research -> synthesis -> reporting)
- Real-time mission activity feed with step-level visibility
- Run trace timeline with durations and token usage
- Start, stop, pause, and rerun controls
- Structured findings with confidence and source attribution

### Expert Agent System

- Dynamic specialist assignment per mission
- Tool-calling loop for each expert task
- Agent thinking logs and delegated task execution
- Built-in specialist roles:
  - Web Researcher
  - Data Analyst
  - Market Analyst
  - Property Researcher
  - Local Scout
  - Voice Caller
  - Synthesizer
  - Report Writer

### Data Collection + Analysis

- Web search + semantic retrieval
- Web page extraction and source parsing
- Python sandbox analysis for stats and transformations
- Chart generation for report sections
- Confidence-scored findings with tags and metadata

### Voice Intelligence

- Outbound call campaigns for primary-source data gathering
- Call transcript ingestion and structured extraction
- Voice session monitoring and call-level drilldown

### Workflow Automation

- Visual workflow editor with DAG nodes
- Workflow templates and custom runs
- Scheduled workflow execution
- Workflow run status tracking and validation endpoints

### Monitoring + Alerts

- Monitor creation for change detection
- Scheduled monitor checks
- Alert severity, acknowledgements, unread counters
- Live feed integration for monitor-driven events

### Intelligence Layer

- Signals ingestion and processing
- Observation + evidence graph
- Insight generation and freshness lifecycle
- Recommendations inbox + accept/reject flows
- Actions/approvals operational pipeline

### Reporting + Sharing

- Mission-to-report generation pipeline
- Rich report sections with charts and citations
- PDF export
- Share links for report delivery
- Findings export: CSV / JSON / Excel

### Realtime + Observability

- WebSocket live event stream (`/ws/live-feed`)
- Redis event bridge
- Run step observability model
- Circuit breaker status in health checks
- Background processing via Celery workers

### Dashboard + UX Surfaces

- Home mission templates
- Projects and mission list views
- Mission live console
- Command Center dashboard
- Reports workspace
- Workflows workspace
- Monitors workspace
- Voice extraction workspace
- Signals / Recommendations / Actions / Approvals / Analytics pages
- Settings and infrastructure health

---

## How It Works

```
You define a mission objective
            |
            v
Gemini assembles the best expert crew
            |
            v
Experts execute tool-calling research tasks in parallel
            |
            v
Findings are scored, sourced, and structured
            |
            v
Synthesizer + Report Writer produce final outputs
            |
            v
You monitor progress live and export/share results
```

---

## Architecture

```
Dashboard (Next.js + TypeScript)
  |-- Pages: missions, projects, workflows, reports, monitors, voice, intelligence
  |-- Realtime UI updates via WebSocket + REST hydration
            |
            v
API Layer (FastAPI)
  |-- Mission orchestration
  |-- Workflow engine
  |-- Voice pipeline
  |-- Reporting services
  |-- Monitoring + alerts
  |-- Signals/insights/recommendations/actions
            |
            v
Execution + Infra
  |-- Gemini 2.5 Flash (generation + tool calling)
  |-- PostgreSQL (core state)
  |-- Redis (queue + pubsub)
  |-- Qdrant (vector/search)
  |-- Celery workers (async task execution)
  |-- APScheduler (timed jobs)
```

---

## API Highlights

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/missions` | Create mission |
| `POST` | `/api/missions/{id}/start` | Start mission execution |
| `GET` | `/api/missions/{id}/status` | Live mission status + activity |
| `GET` | `/api/missions/{id}/findings` | Structured findings |
| `POST` | `/api/workflows/{id}/run` | Trigger workflow |
| `GET` | `/api/runs/{run_id}/steps` | Run-step observability trace |
| `POST` | `/reports/` | Generate report |
| `GET` | `/reports/{id}/pdf` | Export PDF |
| `POST` | `/reports/{id}/share` | Share link |
| `WS` | `/ws/live-feed` | Realtime event stream |
| `GET` | `/health` | Service + breaker health |

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+
- Docker

```bash
git clone https://github.com/madhavcodez/agentary.git
cd agentary

# Infra
docker compose up -d db redis qdrant

# Backend
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd ../dashboard
npm install
npm run dev
```

Open `http://localhost:3000`.

---

## Environment Variables

| Variable | Required | Purpose |
|---|:---:|---|
| `GEMINI_API_KEY` | Yes | Core LLM + tool-calling |
| `DATABASE_URL` | Yes | PostgreSQL |
| `REDIS_URL` | Yes | Queue + pubsub |
| `QDRANT_URL` | Yes | Vector/search backend |
| `EXA_API_KEY` | Optional | Exa semantic web search |
| `TWILIO_ACCOUNT_SID` | Optional | Voice calling |
| `TWILIO_AUTH_TOKEN` | Optional | Voice calling |
| `TWILIO_FROM_NUMBER` | Optional | Voice calling |
| `RESEND_API_KEY` | Optional | Email notifications |

---

## Project Structure

```
agentary/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ models/
│  │  ├─ schemas/
│  │  ├─ services/
│  │  ├─ tasks/
│  │  └─ core/
│  ├─ alembic/
│  └─ tests/
├─ dashboard/
│  ├─ app/
│  ├─ components/
│  └─ lib/
├─ docs/
│  └─ screenshots/
├─ docker-compose.yml
└─ README.md
```

---

<div align="center">

**MIT License**

Built by [Madhav Chauhan](https://github.com/madhavcodez)

</div>
