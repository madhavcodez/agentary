<div align="center">

# AGENTARY

### Autonomous AI Research & Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Deploy expert AI agent crews that research any domain, make voice calls, analyze data, and generate polished reports — automatically.**

[Getting Started](#quick-start) | [Architecture](#architecture) | [Agents](#expert-agents) | [Tools](#tools) | [API](#api-endpoints)

---

</div>

## How It Works

You define a research mission. Agentary does the rest:

```
 You: "Research the AI agents market and competitive landscape"
                              |
                              v
                  +------ AGENTARY ------+
                  |                      |
           Gemini selects 5 experts      |
           Gemini plans 10+ tasks        |
                  |                      |
     +------------+------------+         |
     |            |            |         |
  Web          Market        Data        |
  Researcher   Analyst       Analyst     |
  (3 tasks)    (3 tasks)    (2 tasks)    |
     |            |            |         |
     +-----+------+------+----+         |
           |              |              |
      Synthesizer    Report Writer       |
      (1 task)       (1 task)            |
           |              |              |
           v              v              |
     Ranked findings  PDF report         |
     with confidence  with charts        |
     scores & sources & citations        |
                  |                      |
                  +----------------------+
                              |
                              v
         Real-time activity feed + exportable data
```

## What You Get

| Feature | Description |
|---------|-------------|
| **Live Activity Feed** | Watch agents think, search, scrape, and analyze in real-time |
| **Structured Findings** | Every fact gets a confidence score, source URL, and category |
| **Auto-Generated Reports** | Executive summary, sections, charts, citations, methodology |
| **Multi-Format Export** | CSV, JSON, Excel, PDF, Markdown, shareable link |
| **Visual Workflows** | Drag-and-drop DAG editor for reusable research pipelines |
| **Voice Extraction** | Phone-call campaigns to gather data from businesses directly |
| **Automated Monitors** | Set up watchers that detect changes and send alerts |
| **10 Data Connectors** | Google Places, Yelp, Crunchbase, Zillow, Exa, web scraping, and more |

---

## Architecture

```
+-------------------------------------------------------------------+
|                     DASHBOARD (Next.js 14)                        |
|  21 pages  |  23 components  |  ReactFlow  |  Chart.js  |  WS    |
+-------------------------------------------------------------------+
                               |
                          REST + WebSocket
                               |
+-------------------------------------------------------------------+
|                      API LAYER (FastAPI)                          |
|  34 routers  |  JWT auth  |  rate limiting  |  circuit breakers   |
+-----------+----------+-----------+-----------+--------------------+
|  Crew     | Workflow | Voice     | Report    | Monitor            |
|  Runner   | Engine   | Pipeline  | Generator | Service            |
+-----------+----------+-----------+-----------+--------------------+
|                    GEMINI 2.5 FLASH                               |
|  tool-calling  |  structured output  |  embeddings  |  grounding  |
+-----------+----------+-----------+-----------+--------------------+
| PostgreSQL| Redis    | Qdrant    | Celery    | APScheduler        |
| 36 models | pub/sub  | vectors   | workers   | cron jobs          |
+-----------+----------+-----------+-----------+--------------------+
```

---

## Expert Agents

Every mission gets a custom crew. Gemini picks the best team for the job.

| | Agent | What It Does | Tools |
|---|-------|-------------|-------|
| :mag: | **Web Researcher** | Systematic search with 2+ source corroboration | `gemini_search` `exa_search` `web_scraper` |
| :bar_chart: | **Data Analyst** | Statistical analysis, trend detection, visualizations | `python_executor` `chart_generator` |
| :chart_with_upwards_trend: | **Market Analyst** | Market sizing, SWOT, competitive landscape, pricing | `gemini_search` `exa_search` `web_scraper` `python_executor` |
| :house: | **Property Researcher** | Real estate comps, valuations, neighborhood profiles | `gemini_search` `exa_search` `web_scraper` |
| :round_pushpin: | **Local Scout** | Local business intel, reviews, area demographics | `gemini_search` `exa_search` `web_scraper` `voice_caller` |
| :telephone_receiver: | **Voice Caller** | Phone-based data extraction from businesses | `voice_caller` |
| :brain: | **Synthesizer** | Cross-references findings, resolves contradictions | LLM reasoning only |
| :memo: | **Report Writer** | Executive summaries, sections, charts, citations | `chart_generator` |

Each agent has a detailed system prompt with methodology, output format, and guardrails. Agents use an **agentic tool-calling loop** — up to 6 iterations of Gemini function-calling per task.

---

## Tools

| Tool | Input | Output | Use Case |
|------|-------|--------|----------|
| `gemini_search` | query + focus | search results | Broad web overview |
| `exa_search` | query + type (neural/keyword) | ranked results with snippets | Deep semantic search |
| `web_scraper` | URL + extract mode | text, tables, links | Page content extraction |
| `python_executor` | Python code (sandboxed) | execution output | Data analysis, statistics |
| `voice_caller` | phone + questions | transcript + extracted data | Direct business outreach |
| `chart_generator` | chart type + data | Chart.js config | Data visualization |

---

## Dashboard Pages

| Page | What's There |
|------|-------------|
| **Home** `/` | 6 project templates, one-click creation |
| **Projects** `/projects` | Card grid with type badges, mission/finding counts |
| **Project Detail** `/projects/[id]` | Missions list, findings preview, inline mission creation |
| **Mission Live** `/missions/[id]` | Real-time activity feed, findings cards, structured data table |
| **Command Center** `/dashboard` | Live events, active missions, monitors panel, stats |
| **Workflow Editor** `/workflows/[id]` | ReactFlow canvas, node palette, properties panel |
| **Reports** `/reports/[id]` | Full report with TOC, inline charts, PDF download, sharing |
| **Monitors** `/monitors` | Change detection with cron schedules, alert history |
| **Voice** `/voice` | Extraction campaigns with progress tracking |
| **Settings** `/settings` | Infrastructure health, circuit breaker status |

---

## Quick Start

### Prerequisites
- Python 3.13+, Node.js 18+, Docker

```bash
# Clone
git clone https://github.com/madhavcodez/agentary.git && cd agentary

# Infrastructure
docker compose up -d db redis qdrant

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # set GEMINI_API_KEY
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd dashboard && npm install && npm run dev
```

Open **http://localhost:3000** — pick a research type, name your project, create a mission, hit Start.

### Environment

| Variable | Required | What For |
|----------|:--------:|----------|
| `GEMINI_API_KEY` | **Yes** | LLM, tool-calling, embeddings, structured output |
| `DATABASE_URL` | | PostgreSQL connection (default: localhost) |
| `REDIS_URL` | | Redis for cache, pub/sub, queues (default: localhost) |
| `EXA_API_KEY` | | Neural web search via Exa |
| `TWILIO_ACCOUNT_SID` | | Voice calling |
| `TWILIO_AUTH_TOKEN` | | Voice calling |
| `TWILIO_FROM_NUMBER` | | Voice calling |
| `RESEND_API_KEY` | | Email alerts |

---

## API Endpoints

**34 routers, 100+ endpoints.** Key ones:

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `POST` | `/api/missions` | Create a mission |
| `POST` | `/api/missions/{id}/start` | Assemble crew + execute |
| `GET` | `/api/missions/{id}/status` | Live status + activity feed |
| `GET` | `/api/missions/{id}/findings` | Structured findings with filters |
| `POST` | `/api/workflows` | Create workflow |
| `POST` | `/api/workflows/{id}/run` | Trigger workflow execution |
| `POST` | `/reports/` | Generate report from mission |
| `GET` | `/reports/{id}/pdf` | Download PDF |
| `POST` | `/reports/{id}/share` | Create shareable link |
| `WS` | `/ws/live-feed` | Real-time event stream |
| `GET` | `/health` | Postgres, Redis, Qdrant, circuit breakers |

---

## Data Model

```
Project
  |-- Mission
  |     |-- AgentCrew (auto-assembled)
  |     |     |-- ExpertAgent (Web Researcher, Market Analyst, ...)
  |     |-- CrewRun
  |     |     |-- CrewTask (per-expert, per-phase)
  |     |-- Finding (structured data points with confidence)
  |     |-- Report (generated document with charts)
  |
  |-- Workflow (visual DAG)
  |     |-- WorkflowRun
  |
  |-- Monitor (automated watcher)
  |     |-- Alert
  |
  |-- VoiceExtraction
        |-- CallRecord
```

**36 SQLAlchemy models** across missions, agents, findings, reports, workflows, monitors, voice, entities, data sources, and more.

---

## Project Structure

```
agentary/
+-- backend/
|   +-- app/
|   |   +-- api/                # 34 FastAPI routers
|   |   +-- models/             # 36 SQLAlchemy models
|   |   +-- services/
|   |   |   +-- crews/          # CrewRunner, tool registry, events, expert registry
|   |   |   +-- reports/        # Report generator, PDF export, chart engine
|   |   |   +-- workflow/       # Workflow executor, NL builder
|   |   |   +-- voice/          # Pipecat + Twilio voice pipeline
|   |   |   +-- data_sources/   # 10 external connectors
|   |   +-- core/               # WebSocket manager, Redis pub/sub bridge
|   |   +-- tasks/              # Celery background tasks
|   +-- tests/                  # 556 tests
+-- dashboard/
|   +-- app/                    # 21 Next.js pages
|   +-- components/             # 23 React components
|   +-- lib/                    # API client, types, hooks, auth
+-- docker-compose.yml          # 8-service orchestration
+-- nginx.conf                  # Reverse proxy
```

---

## Dev

```bash
# Tests (556 passing)
cd backend && .venv/bin/python -m pytest tests/ -q

# Frontend build
cd dashboard && npm run build

# Docker (everything)
docker compose up --build
```

---

<div align="center">

**MIT License**

Built by [Madhav Chauhan](https://github.com/madhavcodez)

</div>
