<div align="center">

# AGENTARY

### Autonomous Research & Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5-37814A?style=flat-square&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Qdrant](https://img.shields.io/badge/Qdrant-vector-DC244C?style=flat-square)](https://qdrant.tech)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Flash_+_Pro-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Give Agentary an objective. It scouts the landscape, deep-dives every angle in parallel, audits its own gaps, and delivers a structured, cited report — all autonomously.**

[Overview](#overview) · [System Architecture](#system-architecture) · [Research Pipeline](#research-pipeline) · [Pre-Writing Stage](#pre-writing-stage) · [Expert Agents](#expert-agent-system) · [Data Model](#data-model) · [Quick Start](#quick-start)

</div>

---

## Overview

Agentary is a full-stack platform for autonomous research operations. You describe an objective; the system handles mission planning, multi-source collection, quality auditing, synthesis, and delivery of structured intelligence.

**What it does**

- Decomposes a research objective into an expert-agent execution plan
- Runs multi-source collection in parallel — neural web search, page scraping, outbound voice calls, Python analysis
- Scores, attributes, and structures every finding with confidence and source provenance
- Generates downstream intelligence layers: signals, insights, recommendations
- Produces exportable reports (Markdown / HTML / PDF) with per-section citations, charts, and executive summaries
- Streams execution state to a live dashboard via WebSocket so every micro-action is observable

**Typical use cases** — market intelligence, competitor monitoring, due diligence, lead research, local business data collection, and technology landscape scans.

---

## System Architecture

Agentary is a four-layer system. A Next.js dashboard talks to a FastAPI orchestration layer, which dispatches work to Celery workers backed by PostgreSQL, Redis, and Qdrant.

```
                                 +---------------------+
                                 |    Next.js 14        |
                                 |    Dashboard         |
                                 |  (App Router + WS)   |
                                 +---------+-----------+
                                           |
                              REST + WebSocket (real-time)
                                           |
                                 +---------v-----------+
                                 |    FastAPI           |
                                 |    Orchestration     |
                                 |  (40+ API routes)    |
                                 +---------+-----------+
                                           |
                    +----------------------+----------------------+
                    |                      |                      |
          +---------v------+     +---------v------+     +---------v------+
          |  Celery Workers |     |  PostgreSQL    |     |  Redis         |
          |  (6 queues)     |     |  (50+ tables)  |     |  (broker/pubsub)|
          +--------+--------+     +----------------+     +----------------+
                   |
          +--------v--------+     +-----------------+
          |  AI & External   |<--->|  Qdrant         |
          |  Gemini, Exa,    |     |  (vector store) |
          |  Twilio, Scrapers |     +-----------------+
          +------------------+
```

### Layer 1 — Frontend (`dashboard/`)

Next.js 14 App Router with TypeScript and Tailwind CSS. Routes cover missions, projects, reports, monitors, workflows, entities, signals, recommendations, analytics, voice management, approvals, and settings. Real-time updates stream via WebSocket for mission progress, finding discovery, and report readiness.

### Layer 2 — API & Orchestration (`backend/app/`)

FastAPI serving 40+ endpoints. Core orchestration services:

| Service | Path | Responsibility |
|---------|------|----------------|
| **Crew Runner** | `services/crews/crew_runner.py` | 5-phase execution engine for expert-agent missions |
| **Crew Service** | `services/crews/crew_service.py` | Crew assembly + expert selection |
| **Task Planner** | `services/crews/task_planner.py` | Gemini-powered mission decomposition |
| **Expert Registry** | `services/crews/expert_registry.py` | 10 built-in specialist agents |
| **Tool Registry** | `services/crews/tool_registry.py` | Agentic tool dispatch (search, scrape, call, analyze) |
| **Research Engine** | `services/research/engine.py` | Deep research flow for match / company intelligence |
| **Report Generator** | `services/reports/report_generator.py` | Markdown / HTML / PDF synthesis |
| **Signal Service** | `services/intelligence/signal_service.py` | Signal detection and tracking |
| **Insight Generator** | `services/intelligence/insight_generator.py` | LLM-driven insight synthesis |
| **Workflow Engine** | `services/workflow/service.py` | DAG-based workflow execution |
| **State Machine** | `services/state_machine.py` | Run lifecycle and transition validation |
| **Monitor Service** | `services/monitor_service.py` | Scheduled re-runs and change detection |

### Layer 3 — Data & Execution

- **PostgreSQL** (50+ tables via SQLAlchemy + Alembic): projects, missions, findings, expert agents, crew tasks, reports, entities, signals, insights, recommendations, research outlines, section citations, storm runs, audit logs.
- **Redis**: Celery broker, pub/sub for WebSocket events, budget counters, runtime state cache.
- **Qdrant**: vector embeddings for semantic search across findings, entities, and outline-scope binding.
- **Celery** (6 queues): `research`, `missions`, `voice`, `monitors`, `reports`, `workflows`. Beat scheduler drives periodic monitors and scheduled re-runs.

### Layer 4 — AI & External Integrations

| Integration | Usage |
|-------------|-------|
| **Gemini 2.5 Flash** | Core LLM for reasoning, extraction, tool-calling, outline planning |
| **Gemini 2.5 Pro** | Section-level synthesis where quality matters |
| **Gemini Grounding** | Google Search grounding for live web intelligence |
| **Exa Search** | Neural web search and contact discovery |
| **Web Scraper** | Full-page content extraction from target URLs |
| **Twilio** | Outbound voice calls with transcript capture |
| **Resend** | Email delivery for notifications and report distribution |

---

## Research Pipeline

Every mission executes through a structured five-phase pipeline, inspired by the [DeerFlow](https://github.com/bytedance/deer-flow) deep-research methodology. The goal is to replace single-pass "search → write" loops with a systematic process that explicitly maps dimensions, runs parallel investigations, audits its own gaps, and synthesizes before writing.

```
 PHASE 1           PHASE 2              PHASE 3           PHASE 4           PHASE 5
 ┌──────┐     ┌──────────────┐     ┌────────────┐     ┌───────────┐     ┌──────────┐
 │SCOUT │───>│   RESEARCH    │────>│ GAP CHECK  │────>│ SYNTHESIS │────>│  REPORT  │
 │      │     │  (parallel)  │     │            │     │           │     │          │
 └──────┘     └──────────────┘     └────────────┘     └───────────┘     └──────────┘
  1 expert     N experts ×           1 expert          1 expert          1 expert
  broad        M dimensions          audit pass        merge + assess    structure
  landscape    deep dives            completeness      contradictions    delivery
```

### Phase 1 — Scout

A single expert performs broad exploration to map the research landscape before any deep investigation begins. It surveys the topic, identifies the dimensions, stakeholders, and data sources worth investigating, and produces a structured dimension list for Phase 2. Without scouting, parallel experts dive into whichever angle comes back from the first search query; the scout forces explicit coverage planning first.

### Phase 2 — Research (Parallel Deep Dives)

Multiple expert agents execute in parallel, each assigned to one of the dimensions surfaced by the scout. Every research task targets six explicit information categories — this is the coverage contract a research phase must honor:

| Category | What to Find | Example |
|----------|--------------|---------|
| **Facts & Data** | Statistics, numbers, market sizes, dates | "Series B raised $45M at $200M valuation" |
| **Examples & Cases** | Real-world implementations, incidents | "Stripe deployed this in Q3, cutting fraud 40%" |
| **Expert Opinions** | Analyst perspectives, official statements | "Gartner places this in the Trough of Disillusionment" |
| **Trends & Predictions** | Forward-looking analysis, forecasts | "Market expected to reach $12B by 2028 (CAGR 23%)" |
| **Comparisons** | Alternatives, competitive context | "Unlike Competitor X which uses A, this uses B" |
| **Challenges & Criticisms** | Risks, limitations, opposing views | "Critics note accuracy drops below 60% on edge cases" |

Each expert runs an agentic tool-calling loop (up to 6 iterations per task) powered by Gemini, using `exa_search`, `gemini_search`, `web_scraper`, `python_executor`, `chart_generator`, and `voice_caller` to gather information.

### Phase 3 — Gap Check

After parallel research completes, a synthesizer agent audits the findings against the six diversity categories above, flags under-covered dimensions, and writes gap-notes back into the mission state. This is the quality control pass that prevents the pipeline from over-indexing on whichever angle happened to be easiest to find.

### Phase 4 — Synthesis

The synthesizer receives all findings (including gap-check output), resolves contradictions between sources, weights claims by confidence and source authority, identifies cross-dimension patterns, and produces an overall assessment with explicit confidence levels.

### Phase 5 — Report

The report writer generates a structured output from the synthesized assessment — executive summary, detailed sections, inline charts, source citations, confidence indicators. Exports to Markdown / HTML / PDF; share tokens enable external distribution.

---

## Pre-Writing Stage

The research pipeline above produces good *breadth*. To lift *report quality* — better structure, section-level citations, and less "big-pile-of-sources" feeling — Agentary adds an opt-in pre-writing stage inspired by Stanford's [STORM](https://github.com/stanford-oval/storm) methodology (Shao et al., NAACL 2024).

STORM runs as **Phase 0**: before Scout, the system plans the report outline with stakeholder perspectives, research questions, and section scopes. Findings discovered later in Phase 2 are bound back to those sections so each section cites the specific evidence that supports it, instead of the report ending with one undifferentiated `sources: [...]` array.

Enable per-mission (`missions.storm_enabled=true`) or globally (`AGENTARY_STORM_ENABLED=true`).

```
 PERSPECTIVE        QUESTION             OUTLINE               SECTION              REFINEMENT
 ┌──────────┐    ┌────────────┐     ┌────────────┐     ┌───────────────┐     ┌────────────┐
 │  MINER   │───>│ GENERATOR  │────>│  PLANNER   │────>│  SYNTHESIZER  │────>│  (bounded) │
 │ (Flash)  │    │  (Flash)   │     │  (Flash)   │     │    (Pro)      │     │            │
 └──────────┘    └────────────┘     └────────────┘     └───────────────┘     └────────────┘
  1 call          N calls            1 call             N calls               ≤2 calls
```

### Step 1 — Perspective Mining

`services/storm/perspective_miner.py` discovers up to four distinct stakeholder viewpoints on the topic (e.g. *skeptical regulator*, *beneficiary*, *insider*, *outsider*). Diversity is enforced structurally: if two perspectives' focus-sentence embeddings cosine-similar above 0.85, the batch is rejected and retried with a contrast-emphasis prompt.

### Step 2 — Question Generation

`services/storm/question_generator.py` issues one Gemini Flash call per perspective, producing up to three research questions that perspective would most want answered — each tagged with priority and evidence type (`fact`, `trend`, `comparison`, `expert_opinion`, `example`, `challenge`). N perspectives ⇒ N calls, not N×M.

### Step 3 — Outline Planning

`services/storm/outline_planner.py` consumes the perspective × question matrix in a single Flash call and plans up to six sections, each with a `scope` sentence, `source_question_ids` (≤3), and `expected_evidence_types`. The outline is persisted in the `research_outlines` table — the pre-write is auditable per-mission.

### Step 4 — Evidence Binding

`services/storm/evidence_binder.py` runs after Phase 2 research produces findings. Each section's `scope` is embedded, and the top-K findings (≥0.55 cosine similarity) are bound to it. Pure function — no LLM call. Sections that come out with zero bound findings are flagged for refinement or marked `partial_evidence=true` rather than filled with hallucinated filler.

### Step 5 — Section Synthesis

`services/storm/section_synthesizer.py` issues one Gemini 2.5 Pro call per section. The prompt supplies only that section's bound findings and requires a `citations` array whose `finding_id` values match the bound set exactly. Hallucinated ids are rejected post-parse; a single stricter retry precedes any fallback.

### Step 6 — Bounded Refinement

`services/storm/refinement.py` scores each section on structural quality (citation density, evidence coverage, minimum length) and rewrites the weakest sections. A hard global cap of 2 Pro refinement calls per report keeps cost predictable.

### Section-Level Citation Grounding

Citations are persisted as structural rows, not prompt-promise markup. The `section_citations` table stores `(report_id, section_index, finding_id, quote_span, confidence)` — so "show me the evidence for section 3 of report X" is a plain `SELECT`:

```sql
SELECT s.section_index, f.source_url, s.quote_span, s.confidence
FROM section_citations s
JOIN findings f ON s.finding_id = f.id
WHERE s.report_id = :report_id
ORDER BY s.section_index, s.confidence DESC;
```

### Gemini Budget Discipline

STORM's canonical fan-out (perspectives × questions × sections) can easily hit 40+ calls per mission. Agentary caps total spend at **14 calls per report** through a Redis-backed counter (`services/storm/budget.py`):

| Stage | Model | Max calls |
|-------|-------|-----------|
| Perspective mining | Flash | 1 |
| Question generation | Flash | N (≤4) |
| Outline planning | Flash | 1 |
| Section synthesis | Pro | M (≤6) |
| Refinement | Pro | ≤2 |
| **Total** | | **6 Flash + 8 Pro = 14** |

Budget breach raises `StormBudgetExceeded`; the runner silently falls back to the baseline synthesizer, logs the fallback reason to the `storm_runs` telemetry table, and the mission still completes.

### STORM vs Baseline Pipeline

| Aspect | Baseline (DeerFlow only) | With STORM |
|--------|--------------------------|------------|
| Phase count | 5 | 6 (pre-write added) |
| Report outline | Derived from findings after the fact | Planned before retrieval |
| Perspective coverage | Expert specialties | Mined stakeholder viewpoints |
| Citation binding | Global `sources[]` array | Per-section `SectionCitation` rows |
| Quality gate | None post-synthesis | Structural metrics + bounded refinement |
| Citation validation | Prompt convention | Post-parse `finding_id` check |
| Gemini spend | 1 call per mission | 6 Flash + ≤8 Pro per mission |

---

## Execution Pipeline

### Mission Lifecycle

```
User creates Mission
       |
       v
  POST /api/missions/{id}/run
       |
       v
  +-----------------------+
  |  Celery: plan_and_    |
  |  start_mission()      |
  |                       |
  |  1. Load mission      |
  |  2. Select experts    |   Gemini picks the best agents
  |     (Gemini)          |   for the mission objective
  |  3. Assemble crew     |
  |  4. Plan tasks        |   5-phase task plan
  |     (DeerFlow phases) |
  |  5. Create CrewRun    |
  +-----------+-----------+
              |
              v
  +-----------------------+
  |  Celery: execute_     |
  |  crew_run()           |
  |                       |
  |  Phase 0: Pre-write   |─> STORM (opt-in): outline, perspectives
  |  Phase 1: Scout       |─> 1 expert, broad exploration
  |  Phase 2: Research    |─> N experts in parallel, deep dives
  |  Phase 3: Gap Check   |─> 1 expert, audit completeness
  |  Phase 4: Synthesis   |─> 1 expert, merge + assess
  |  Phase 5: Report      |─> 1 expert, structured output
  +-----------+-----------+
              |
              v
  +-----------------------+
  |  Intelligence Layer   |
  |                       |
  |  Findings ──> Signals |
  |  Signals ──> Insights |
  |  Insights ──> Recs    |
  |  Recs ──> Actions     |
  +-----------+-----------+
              |
              v
  +-----------------------+
  |  WebSocket broadcast  |
  |  to dashboard         |
  +-----------------------+
```

### Agentic Tool-Calling Loop

Each expert task runs a Gemini-driven tool-calling loop:

```
Expert receives task prompt
       |
       v
  ┌─── Loop (max 6 iterations) ───┐
  |                                |
  |  Gemini generates response     |
  |       |                        |
  |  Has function_call?            |
  |    Yes: execute tool           |
  |         append result          |
  |         continue loop ─────────┘
  |    No:  parse findings
  |         store to DB
  |         emit RunStep events
  |         done
  └────────────────────────────────┘
```

Tools available inside the loop:

| Tool | Purpose |
|------|---------|
| `exa_search` | Neural web search via Exa API |
| `gemini_search` | Google Search grounding via Gemini |
| `web_scraper` | Full-page content extraction |
| `python_executor` | Run Python for numeric analysis |
| `chart_generator` | Generate inline report visualizations |
| `voice_caller` | Outbound phone calls via Twilio |

### State Machine

Mission runs follow a strict state machine with validated transitions:

```
created ──> queued ──> running ──> completed
                         |
                         +──> partially_failed ──> completed
                         |                    └──> failed
                         +──> retrying ──> running
                         |
                         +──> failed
                         |
                         +──> cancelled
```

Every transition is persisted with timestamp and reason. Idempotency keys prevent duplicate execution. Failure categories (`transient`, `model_error`, `rate_limited`, `timeout`, `validation`, `internal`) drive targeted retry logic.

### Observability

Every micro-action during execution is recorded as a `RunStep`:

| Step Type | When Recorded |
|-----------|---------------|
| `expert_task` | Expert begins / completes a task |
| `tool_call` | Tool executed, with input / output |
| `searching` | Scout-phase exploration |
| `analyzing` | Gap-check audit |
| `synthesis` | Synthesis-phase merge |
| `writing` | Report generation |
| `error` | Any failure during execution |

RunSteps carry correlation IDs, parent-child relationships, token counts, duration, and truncated input/output summaries. Full execution replay is possible from the DB alone — no ephemeral state.

---

## Expert Agent System

Agentary ships with 10 built-in expert agents. Each expert declares a specialty, a system prompt, a tool allow-list, and a model configuration.

| Expert | Specialty | Tools | Role |
|--------|-----------|-------|------|
| **Web Researcher** | `web_researcher` | exa_search, gemini_search, web_scraper | Scout + Research |
| **Data Extractor** | `data_extractor` | exa_search, web_scraper, python_executor | Research |
| **Market Analyst** | `market_analyst` | gemini_search, exa_search, python_executor | Research |
| **Financial Analyst** | `financial_analyst` | gemini_search, python_executor | Research |
| **Competitive Intel** | `competitive_intel` | exa_search, gemini_search, web_scraper | Scout + Research |
| **Due Diligence** | `due_diligence` | exa_search, gemini_search | Research |
| **Local Business Intel** | `local_business_intel` | exa_search, web_scraper, voice_caller | Research |
| **Voice Caller** | `voice_caller` | voice_caller | Research (phone extraction) |
| **Synthesizer** | `synthesizer` | — (reasoning only) | Gap Check + Synthesis |
| **Report Writer** | `report_writer` | chart_generator, python_executor | Report |

Experts are selected per-mission by Gemini based on the objective. Custom experts can be registered via the API.

---

## Data Model

### Core Entities

```
Project (scoping container)
  └── Mission (research task)
        ├── AgentCrew (selected experts)
        ├── ResearchOutline (STORM pre-write, optional)
        │     └── SectionCitation (per-section evidence binding)
        ├── MissionRun (execution instance)
        │     ├── CrewTask (per-expert task)
        │     │     └── RunStep (micro-action trace)
        │     └── CrewRun (crew execution record)
        ├── Finding (discovered data point)
        └── Report (synthesized output)

Finding
  ├── type: fact | insight | statistic | contact_info | trend | risk | opportunity | ...
  ├── source: web | voice_call | api | public_record | inferred
  ├── confidence: 0.0 – 1.0
  └── entity_refs: linked entities

Intelligence Pipeline
  Finding ──> Signal ──> Insight ──> Recommendation ──> Action
```

### Key Enums

| Enum | Values |
|------|--------|
| **MissionType** | research, voice_extraction, monitoring, data_collection, competitive_analysis, custom |
| **CoordinationStrategy** | parallel, sequential, hierarchical |
| **FindingType** | fact, data_point, insight, quote, statistic, contact_info, price, trend, anomaly, opportunity, risk |
| **RunStatus** | created, queued, running, awaiting_input, retrying, partially_failed, completed, failed, cancelled |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14 (App Router), TypeScript 5, Tailwind CSS, WebSocket live state |
| **API** | FastAPI 0.115, Pydantic v2, 40+ route modules |
| **Async Execution** | Celery 5 (6 queues + Beat scheduler), Redis broker |
| **Primary DB** | PostgreSQL 16, SQLAlchemy, Alembic migrations (50+ tables) |
| **Vector Store** | Qdrant (finding + outline-scope embeddings) |
| **Cache / Pub-Sub** | Redis 7 (WebSocket events, STORM budget counters, runtime state) |
| **LLM — reasoning** | Gemini 2.5 Flash (extraction, tool-calling, outline planning) |
| **LLM — synthesis** | Gemini 2.5 Pro (section-level writing, refinement) |
| **Grounding** | Gemini Grounding (Google Search), Exa neural search |
| **Web** | Custom scraper (HTTP + HTML parse) |
| **Voice** | Twilio (outbound calls + transcript capture) |
| **Email** | Resend |
| **Container** | Docker + docker-compose (db, redis, qdrant, backend, dashboard, nginx) |

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+
- Docker + Docker Compose

```bash
git clone https://github.com/madhavcodez/agentary.git
cd agentary

# 1. Infrastructure
docker compose up -d db redis qdrant

# 2. Backend
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Celery workers (new terminal)
celery -A app.celery_app worker --loglevel=info --queues=research,missions,voice,monitors,reports,workflows
celery -A app.celery_app beat --loglevel=info

# 4. Frontend (new terminal)
cd ../dashboard
npm install
npm run dev
```

- Dashboard: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

---

## Environment Variables

| Variable | Required | Purpose |
|----------|:--------:|---------|
| `GEMINI_API_KEY` | ✓ | Core LLM (reasoning, tool-calling, synthesis) |
| `DATABASE_URL` | ✓ | PostgreSQL connection string |
| `REDIS_URL` | ✓ | Celery broker + pub/sub |
| `QDRANT_URL` | ✓ | Vector search backend |
| `EXA_API_KEY` |   | Exa neural web search and contact discovery |
| `TWILIO_ACCOUNT_SID` |   | Outbound voice calling |
| `TWILIO_AUTH_TOKEN` |   | Voice call authentication |
| `TWILIO_FROM_NUMBER` |   | Voice caller ID |
| `RESEND_API_KEY` |   | Email delivery |
| `AGENTARY_STORM_ENABLED` |   | Globally enable STORM pre-writing (default: `false`) |
| `STORM_MAX_PERSPECTIVES` |   | Max stakeholder perspectives (default: 4) |
| `STORM_MAX_QUESTIONS` |   | Max questions per perspective (default: 3) |
| `STORM_MAX_SECTIONS` |   | Max outline sections (default: 6) |
| `STORM_MAX_REFINEMENT` |   | Max refinement passes per report (default: 2) |
| `STORM_EVIDENCE_THRESHOLD` |   | Min cosine similarity for evidence binding (default: 0.55) |

---

## Project Structure

```
agentary/
├── backend/
│   ├── app/
│   │   ├── api/              # 40+ FastAPI route modules
│   │   ├── models/           # 50+ SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── crews/        # 5-phase execution engine
│   │   │   │   ├── crew_runner.py      # Phase orchestrator
│   │   │   │   ├── crew_service.py     # Crew assembly
│   │   │   │   ├── task_planner.py     # Gemini task decomposition
│   │   │   │   ├── expert_registry.py  # 10 built-in experts
│   │   │   │   └── tool_registry.py    # Agentic tool dispatch
│   │   │   ├── storm/        # Pre-writing stage (Phase 0)
│   │   │   │   ├── perspective_miner.py
│   │   │   │   ├── question_generator.py
│   │   │   │   ├── outline_planner.py
│   │   │   │   ├── evidence_binder.py
│   │   │   │   ├── section_synthesizer.py
│   │   │   │   ├── refinement.py
│   │   │   │   ├── budget.py
│   │   │   │   └── telemetry.py
│   │   │   ├── research/     # Deep research engine (Gemini + Exa)
│   │   │   ├── intelligence/ # Signals, insights, recommendations
│   │   │   ├── reports/      # Report generation + export
│   │   │   ├── workflow/     # DAG-based workflow execution
│   │   │   ├── voice/        # Voice call orchestration
│   │   │   ├── monitors/     # Scheduled re-runs + change detection
│   │   │   └── state_machine.py   # Run lifecycle
│   │   ├── tasks/            # Celery async tasks (6 queues)
│   │   ├── core/             # Logging, events, rate limits, WebSocket
│   │   ├── providers/        # LLM provider integrations
│   │   └── prompts/          # System prompts for expert agents
│   ├── alembic/              # Database migrations
│   └── tests/                # pytest test suite
├── dashboard/
│   ├── app/                  # Next.js 14 App Router
│   ├── components/           # Reusable UI components
│   └── lib/                  # API client, types, hooks
├── docker-compose.yml
├── nginx.conf
└── README.md
```

---

<div align="center">

**MIT License** · Built by [Madhav Chauhan](https://github.com/madhavcodez)

</div>
