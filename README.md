<div align="center">

# AGENTARY

### Autonomous Research and Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Define an objective, run multi-step research missions, and get structured outputs (signals, actions, reports) from one unified system.**

[Description](#description) · [Architecture Breakdown](#architecture-breakdown) · [Quick Start](#quick-start) · [Project Structure](#project-structure)

</div>

---

## Description

Agentary is a full-stack platform for autonomous research operations.

You provide a mission objective, and the system handles:

- planning and task orchestration
- multi-source collection (web/data/voice)
- structured findings and confidence scoring
- intelligence generation (signals, insights, recommendations)
- controlled execution through approvals and actions
- report/export delivery

Use cases include market intelligence, competitor monitoring, due diligence, and local business data collection.

---

## Architecture Breakdown

### 1) Frontend Layer (`dashboard/`)

- Next.js App Router + TypeScript + TailwindCSS
- Mission control and operational views (missions, workflows, reports, monitors, approvals, analytics)
- Live updates through WebSocket + REST hydration

### 2) API & Orchestration Layer (`backend/app/`)

- FastAPI router surface for core resources and workflows
- Mission runner and expert-agent crew orchestration
- Workflow DAG execution
- Voice extraction orchestration
- Intelligence pipeline: findings -> signals -> insights -> recommendations -> actions
- Reporting services (narrative, charts, export)

### 3) Data & Execution Layer

- PostgreSQL: primary relational data and migrations
- Redis: queueing, pub/sub, and runtime state
- Qdrant: vector search for semantic retrieval
- Celery + scheduler: asynchronous execution for missions, monitors, reports, workflows, and actions

### 4) AI & Integrations Layer

- Gemini for generation, reasoning, extraction, and tool-calling
- External connectors for web and domain data sources
- Voice stack integrations for outbound calls and transcript processing

---

## End-to-End Flow

1. User creates project + mission objective
2. System builds execution plan and selects agents/tools
3. Collection runs in parallel (web/data/voice)
4. Findings are normalized, scored, and attributed
5. Intelligence and recommendations are generated
6. Actions execute with policy/approval gates
7. Reports and exports are produced

---

## API Docs

- Local Swagger UI: `http://localhost:8000/docs`

---

## Quick Start

### Prerequisites
- Python 3.13+
- Node.js 18+
- Docker

```bash
git clone https://github.com/madhavcodez/agentary.git
cd agentary

# Infrastructure
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
| `GEMINI_API_KEY` | Yes | Core LLM + tool calling |
| `DATABASE_URL` | Yes | PostgreSQL connection |
| `REDIS_URL` | Yes | Queue + pub/sub |
| `QDRANT_URL` | Yes | Vector search backend |
| `EXA_API_KEY` | Optional | Exa semantic web search |
| `TWILIO_ACCOUNT_SID` | Optional | Voice calling |
| `TWILIO_AUTH_TOKEN` | Optional | Voice calling |
| `TWILIO_FROM_NUMBER` | Optional | Voice calling |
| `RESEND_API_KEY` | Optional | Email notifications |

---

## Project Structure

```
agentary/
├── backend/
│   ├── app/
│   │   ├── api/          # 40+ FastAPI routers
│   │   ├── models/       # 45 SQLAlchemy models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic (crews, intelligence, voice, reports)
│   │   ├── tasks/        # Celery async tasks
│   │   ├── core/         # Logging, events, permissions, WebSocket
│   │   └── providers/    # LLM provider integrations
│   ├── alembic/          # Database migrations
│   └── tests/            # pytest test suite
├── dashboard/
│   ├── app/              # Next.js 14 App Router (28 routes)
│   ├── components/       # Reusable UI components
│   └── lib/              # API client, types, hooks
├── docs/
├── docker-compose.yml
└── README.md
```

---

**MIT License** — Built by [Madhav Chauhan](https://github.com/madhavcodez)
