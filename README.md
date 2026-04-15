<div align="center">

# AGENTARY

### Autonomous Research and Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Define an objective. Agentary scouts the landscape, deep-dives every angle in parallel, audits its own gaps, and delivers structured intelligence — all autonomously.**

[Architecture](#architecture) · [DeerFlow](#deerflow-research-methodology) · [STORM](#stanford-storm-methodology) · [Execution Pipeline](#execution-pipeline) · [Quick Start](#quick-start) · [Project Structure](#project-structure)

</div>

---

## What Is Agentary

Agentary is a full-stack platform for autonomous research operations. You provide a mission objective, and the system handles everything from research planning through intelligence delivery.

**What it does:**
- Plans and decomposes research missions into expert-agent tasks
- Runs multi-source collection in parallel (web search, data extraction, voice calls)
- Scores, attributes, and structures every finding with confidence levels
- Generates intelligence layers (signals, insights, recommendations)
- Produces exportable reports with executive summaries, charts, and citations

**Use cases:** Market intelligence, competitor monitoring, due diligence, lead research, local business data collection, technology landscape analysis.

---

## Architecture

Agentary is a four-layer system: a Next.js dashboard talks to a FastAPI orchestration layer, which dispatches work to Celery workers backed by PostgreSQL, Redis, and Qdrant.

```
                                 +---------------------+
                                 |    Next.js 14       |
                                 |    Dashboard        |
                                 |  (App Router + WS)  |
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
          +---------v------+    +---------v------+    +---------v------+
          |  Celery Workers |    |  PostgreSQL    |    |  Redis         |
          |  (6 queues)     |    |  (50+ tables)  |    |  (queue/pubsub)|
          +--------+--------+    +----------------+    +----------------+
                   |
          +--------v--------+
          |  AI + External   |
          |  Gemini, Exa,    |
          |  Twilio, Scrapers|
          +------------------+
```

### Layer 1: Frontend (`dashboard/`)

Next.js 14 App Router with TypeScript and Tailwind CSS. 28 routes covering missions, projects, reports, monitors, workflows, analytics, voice management, and settings. Real-time updates via WebSocket for mission progress, finding discovery, and report readiness.

### Layer 2: API and Orchestration (`backend/app/`)

FastAPI serving 40+ endpoints. Core orchestration services:

| Service | Path | Responsibility |
|---------|------|----------------|
| **Crew Runner** | `services/crews/crew_runner.py` | Expert-agent execution engine (DeerFlow 5-phase) |
| **Task Planner** | `services/crews/task_planner.py` | Gemini-powered mission decomposition |
| **Expert Registry** | `services/crews/expert_registry.py` | 10 builtin specialist agents |
| **Tool Registry** | `services/crews/tool_registry.py` | Agentic tool dispatch (search, scrape, call, analyze) |
| **Research Engine** | `services/research/engine.py` | Deep research for match/company intel |
| **Report Generator** | `services/reports/report_generator.py` | Markdown/HTML synthesis from findings |
| **Signal Service** | `services/intelligence/signal_service.py` | Signal detection and tracking |
| **Insight Generator** | `services/intelligence/insight_generator.py` | LLM-driven insight synthesis |
| **Workflow Engine** | `services/workflow/service.py` | DAG-based workflow execution |
| **State Machine** | `services/state_machine.py` | Run lifecycle and transition validation |

### Layer 3: Data and Execution

- **PostgreSQL** (50+ tables): Projects, missions, findings, expert agents, crew tasks, reports, entities, signals, insights, recommendations, audit logs. Full migration history via Alembic.
- **Redis**: Celery task broker, pub/sub for WebSocket events, runtime state caching.
- **Qdrant**: Vector embeddings for semantic search across findings and entities.
- **Celery** (6 queues): `research`, `missions`, `voice`, `monitors`, `reports`, `workflows`. Beat scheduler for periodic monitoring.

### Layer 4: AI and Integrations

| Integration | Usage |
|-------------|-------|
| **Gemini 2.5 Flash** | Core LLM for reasoning, extraction, tool-calling, and report synthesis |
| **Gemini Grounding** | Google Search grounding for live web intelligence |
| **Exa Search** | Neural web search and contact discovery |
| **Web Scraper** | Content extraction from target URLs |
| **Twilio** | Outbound voice calls with transcript extraction |
| **Resend** | Email delivery for notifications and reports |

---

## DeerFlow Research Methodology

Agentary's crew execution engine implements the [DeerFlow](https://github.com/bytedance/deer-flow) deep-research methodology — a systematic, multi-phase approach that replaces single-pass research with structured, multi-angle investigation.

### The Problem with Single-Pass Research

A naive research agent calls a search tool once, reads the results, and writes a report. This produces shallow output that misses critical angles, lacks opposing viewpoints, and often relies on whatever the first search query happened to return.

### The DeerFlow Solution: 5-Phase Research Pipeline

Every mission in Agentary now executes through five sequential phases, each with a distinct purpose:

```
 PHASE 1          PHASE 2              PHASE 3           PHASE 4          PHASE 5
 ┌──────┐    ┌──────────────┐     ┌────────────┐    ┌───────────┐    ┌──────────┐
 │SCOUT │───>│   RESEARCH   │────>│ GAP CHECK  │───>│ SYNTHESIS │───>│  REPORT  │
 │      │    │  (parallel)  │     │            │    │           │    │          │
 └──────┘    └──────────────┘     └────────────┘    └───────────┘    └──────────┘
  1 expert    N experts x          1 expert          1 expert         1 expert
  broad       M dimensions         audit pass        merge + assess   structure
  landscape   deep dives           completeness      contradictions   delivery
```

#### Phase 1 — Scout

A single expert performs broad exploration to map the research landscape before any deep investigation begins.

**What it does:**
- Surveys the topic with initial searches to understand overall context
- Identifies key dimensions, subtopics, and angles that need deeper investigation
- Maps stakeholders, perspectives, and data sources
- Produces a structured list of research dimensions for Phase 2

**Why it matters:** Without scouting, research experts dive into whatever angle happens to come up first. The scout ensures every important dimension gets dedicated attention.

#### Phase 2 — Research (Parallel Deep Dives)

Multiple expert agents execute in parallel, each assigned to different research dimensions identified by the scout. Every research task targets six information categories:

| Category | What to Find | Example |
|----------|-------------|---------|
| **Facts & Data** | Statistics, numbers, market sizes, dates | "Series B raised $45M at $200M valuation" |
| **Examples & Cases** | Real-world implementations, incidents | "Stripe deployed this in Q3, reducing fraud by 40%" |
| **Expert Opinions** | Analyst perspectives, official statements | "Gartner places this in the Trough of Disillusionment" |
| **Trends & Predictions** | Forward-looking analysis, forecasts | "Market expected to reach $12B by 2028 (CAGR 23%)" |
| **Comparisons** | Alternatives, competitive context | "Unlike Competitor X which uses approach A, this uses B" |
| **Challenges & Criticisms** | Risks, limitations, opposing views | "Critics argue the accuracy drops below 60% on edge cases" |

Each expert runs an agentic tool-calling loop (up to 6 iterations per task) powered by Gemini, using tools like `exa_search`, `gemini_search`, `web_scraper`, and `python_executor` to gather information.

#### Phase 3 — Gap Check

After all research completes, a synthesizer agent audits the collected findings against the six diversity categories above.

**What it does:**
- Receives a summary of all findings gathered in Phase 2
- Evaluates which categories are well-covered and which have gaps
- Identifies missing perspectives, data types, or viewpoints
- Produces findings that flag research gaps for the synthesis phase

**Why it matters:** Without gap checking, research tends to over-index on whatever angle was easiest to find and under-index on contrarian viewpoints, hard data, or forward-looking analysis. The gap check enforces research quality before synthesis begins.

#### Phase 4 — Synthesis

The synthesizer receives all findings (including gap-check results) and produces a unified assessment.

**What it does:**
- Resolves contradictions between sources
- Weights findings by confidence scores and source authority
- Identifies patterns across dimensions
- Produces an overall assessment with confidence levels

#### Phase 5 — Report

The report writer generates a structured output from the synthesized assessment.

**What it does:**
- Produces executive summary, detailed sections, and charts
- Includes source citations and confidence indicators
- Exports to Markdown, HTML, or PDF
- Generates share tokens for external distribution

### How This Differs from Standard Agent Architectures

| Aspect | Standard Agent | Agentary (DeerFlow) |
|--------|---------------|---------------------|
| Research planning | Ad-hoc or single-pass | Scout phase maps dimensions first |
| Parallel execution | Agents run independently | Dimension-aware parallel deep dives |
| Quality control | None before synthesis | Gap check audits 6 diversity categories |
| Depth per topic | 1-2 search queries | Multi-angle with 6 category coverage |
| Self-correction | No | Gap check identifies missing angles |
| Observability | Limited | RunStep traces every micro-action |

---

## Stanford STORM Methodology

DeerFlow tells Agentary *how* to spread research across five phases. Stanford's [STORM](https://github.com/stanford-oval/storm) (Shao et al., NAACL 2024) tells it *how to pre-write before research* — and that pre-writing discipline is where report quality actually gets locked in.

STORM is opt-in and stacks on top of the DeerFlow pipeline. When `AGENTARY_STORM_ENABLED=true` (or per-mission `storm_enabled=true`), a Phase 0 runs *before* Scout and produces a persisted `ResearchOutline` that steers the rest of the run.

### The Problem STORM Solves

DeerFlow's 5 phases prevent *breadth* failure — scout + gap check ensure every dimension gets investigated. But they don't prevent *structure* failure: the report gets organized *after* findings arrive, so the outline reflects what research happened to return rather than what the topic actually requires. And citations end up at report level (one big `sources: [...]` array) rather than bound to the claim each source supports.

STORM's insight is that pre-writing quality correlates with final-report quality. If you plan the outline *before* retrieval — and commit to specific perspectives, specific questions, and specific section scopes — the synthesizer is grounding claims against a targeted evidence set rather than picking whatever findings look adjacent.

### The STORM Pre-Writing Stage (Phase 0)

```
 PERSPECTIVE        QUESTION            OUTLINE              SECTION             REFINEMENT
 ┌──────────┐    ┌────────────┐     ┌────────────┐     ┌───────────────┐    ┌────────────┐
 │  MINER   │───>│ GENERATOR  │────>│  PLANNER   │────>│  SYNTHESIZER  │───>│  (bounded) │
 │ (Flash)  │    │  (Flash)   │     │  (Flash)   │     │    (Pro)      │    │            │
 └──────────┘    └────────────┘     └────────────┘     └───────────────┘    └────────────┘
  1 call          N calls            1 call             N calls              ≤2 calls
```

**Step 1 — Perspective Mining** (`backend/app/services/storm/perspective_miner.py`)
Discovers ≤4 distinct stakeholder viewpoints on the mission topic (e.g. *skeptical regulator*, *beneficiary*, *insider*, *outsider*). Diversity is enforced structurally — if two perspectives' focus-sentence embeddings cosine-similar above 0.85, the batch is rejected and retried once with a contrast-emphasis prompt.

**Step 2 — Question Generation** (`backend/app/services/storm/question_generator.py`)
One Gemini Flash call per perspective returns up to 3 research questions that perspective would most want answered — tagged with priority and evidence type (`fact`, `trend`, `comparison`, `expert_opinion`, `example`, `challenge`). N perspectives produce at most N calls, not N×M.

**Step 3 — Outline Planning** (`backend/app/services/storm/outline_planner.py`)
One Flash call consumes the perspective × question matrix and plans up to 6 sections, each with a `scope` sentence, `source_question_ids` (≤3), and `expected_evidence_types`. This outline is persisted in `research_outlines` — the whole pre-write is auditable per-mission.

**Step 4 — Evidence Binding** (`backend/app/services/storm/evidence_binder.py`)
After Phase 2 research produces findings, each section's `scope` is embedded and the top-K findings (≥0.55 cosine similarity) are bound to it. Pure function, no LLM call. Sections with zero bound findings are flagged for refinement or skipped rather than filled with hallucination.

**Step 5 — Section Synthesis** (`backend/app/services/storm/section_synthesizer.py`)
One Gemini 2.5 Pro call per section. The prompt supplies only that section's bound findings and requires a `citations` array whose `finding_id` values match the bound set exactly. Hallucinated ids are rejected post-parse; a single retry with a stricter prompt precedes any fallback to `partial_evidence=true`.

**Step 6 — Bounded Refinement** (`backend/app/services/storm/refinement.py`)
A structural quality gate (citation density, evidence coverage, minimum length) scores each section. Weakest sections get a rewrite pass using the refinement prompt. Global cap of 2 additional Pro calls per report — no LLM-as-judge (that would double Pro spend for no defensible gain).

### Section-Level Citation Grounding

STORM-generated reports persist per-section citations as structural rows, not prompt-promise markup. The `section_citations` table stores `(report_id, section_index, finding_id, quote_span, confidence)` so "show me the evidence for section 3 of report X" is a `SELECT`:

```sql
SELECT s.section_index, f.source_url, s.quote_span, s.confidence
FROM section_citations s
JOIN findings f ON s.finding_id = f.id
WHERE s.report_id = :report_id
ORDER BY s.section_index, s.confidence DESC;
```

### Gemini Budget Discipline

STORM's canonical fan-out (perspectives × questions × sections) can easily hit 40+ calls per mission. Agentary caps the total at **14 calls per report** through a Redis-backed counter (`backend/app/services/storm/budget.py`):

| Stage | Model | Max calls |
|---|---|---|
| Perspective mining | Flash | 1 |
| Question generation | Flash | N (≤4) |
| Outline planning | Flash | 1 |
| Section synthesis | Pro | M (≤6) |
| Refinement | Pro | ≤2 |
| **Total** | | **6 Flash + 8 Pro = 14** |

Budget breach raises `StormBudgetExceeded` and the runner falls back to the legacy DeerFlow synthesis path silently — STORM never brings the mission down.

### STORM vs. DeerFlow in Agentary

| Aspect | DeerFlow only | STORM + DeerFlow |
|---|---|---|
| Phase structure | 5 phases (Scout → Report) | 6 phases (Pre-write → Report) |
| Report outline | Derived from findings | Planned before retrieval |
| Perspective coverage | Expert specialties | Mined stakeholder viewpoints |
| Citation binding | Global `sources[]` array | Per-section `SectionCitation` rows |
| Quality gate | None post-synthesis | Structural metrics + bounded refinement |
| Citation validation | Prompt convention | Post-parse `finding_id` check |
| Gemini calls | 1 per mission | 6 Flash + ≤8 Pro per mission |

### Feature Flag & Fallback

```bash
# Global switch (disabled by default)
export AGENTARY_STORM_ENABLED=true

# Optional caps (defaults shown)
export STORM_MAX_PERSPECTIVES=4
export STORM_MAX_QUESTIONS=3
export STORM_MAX_SECTIONS=6
export STORM_MAX_REFINEMENT=2
export STORM_EVIDENCE_THRESHOLD=0.55
```

Per-mission override: set `missions.storm_enabled=true` to opt in a specific mission regardless of the global flag. Any failure in the STORM pipeline (budget exceeded, outline empty, Gemini 503) falls back to the legacy single-pass synthesizer with the fallback reason recorded in the `storm_runs` telemetry table.

### Why This Integration Is Defensible

Every phrase in the STORM resume bullet maps to a file and a queryable row:

| Claim | Code | Evidence |
|---|---|---|
| "Stanford STORM-inspired" | `backend/app/services/storm/` package | Named after the paper; maps pre-writing → writing split directly |
| "perspective-guided question generation" | `perspective_miner.py` + `question_generator.py` | `SELECT perspectives, question_matrix FROM research_outlines WHERE mission_id=X` |
| "outline-first planning" | `outline_planner.py` | Outline row persists before Scout phase runs |
| "section-level citation grounding" | `section_citation.py` + `evidence_binder.py` + `section_synthesizer.py` | Post-validated `finding_id` FK per section, not prompt-promise markup |
| "tiered model routing" | `section_synthesizer.SECTION_MODEL = "gemini-2.5-pro"`; everything else is Flash | `budget.py` caps Flash and Pro independently |
| "bounded refinement" | `refinement.py` | Hard global cap of 2 Pro refinement calls per report |

For deeper interview prep (expected questions, code pointers, known limitations), see [`backend/docs/STORM.md`](backend/docs/STORM.md).

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
  |  2. Select experts    |     Gemini selects best agents
  |     (Gemini)          |     for the mission objective
  |  3. Assemble crew     |
  |  4. Plan tasks        |     Gemini decomposes into
  |     (DeerFlow phases) |     5-phase task plan
  |  5. Create CrewRun    |
  +-----------+-----------+
              |
              v
  +-----------------------+
  |  Celery: execute_     |
  |  crew_run()           |
  |                       |
  |  CrewRunner.          |
  |  execute_run()        |
  |                       |
  |  Phase 1: Scout       |──> 1 expert, broad exploration
  |  Phase 2: Research    |──> N experts in parallel, deep dives
  |  Phase 3: Gap Check   |──> 1 expert, audit completeness
  |  Phase 4: Synthesis   |──> 1 expert, merge + assess
  |  Phase 5: Report      |──> 1 expert, structured output
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

### Expert Agent System

Agentary ships with 10 builtin expert agents. Each expert has a specialty, system prompt, tool access, and model configuration.

| Expert | Specialty | Tools | Role in Pipeline |
|--------|-----------|-------|------------------|
| **Web Researcher** | `web_researcher` | exa_search, gemini_search, web_scraper | Scout + Research phases |
| **Data Extractor** | `data_extractor` | exa_search, web_scraper, python_executor | Research phase |
| **Market Analyst** | `market_analyst` | gemini_search, exa_search, python_executor | Research phase |
| **Financial Analyst** | `financial_analyst` | gemini_search, python_executor | Research phase |
| **Competitive Intel** | `competitive_intel` | exa_search, gemini_search, web_scraper | Scout + Research phases |
| **Due Diligence** | `due_diligence` | exa_search, gemini_search | Research phase |
| **Local Business Intel** | `local_business_intel` | exa_search, web_scraper, voice_caller | Research phase |
| **Voice Caller** | `voice_caller` | voice_caller | Research phase (phone extraction) |
| **Synthesizer** | `synthesizer` | (none — reasoning only) | Gap Check + Synthesis phases |
| **Report Writer** | `report_writer` | chart_generator, python_executor | Report phase |

Experts are selected per-mission by Gemini based on the objective. Custom experts can be created via the API.

### Agentic Tool-Calling Loop

Each expert task runs a Gemini-powered agentic loop:

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
  |         emit events
  |         done
  └────────────────────────────────┘
```

Tools available during the loop:

| Tool | Purpose |
|------|---------|
| `exa_search` | Neural web search via Exa API |
| `gemini_search` | Google Search grounding via Gemini |
| `web_scraper` | Full-page content extraction |
| `python_executor` | Run Python for data analysis |
| `chart_generator` | Generate visualizations |
| `voice_caller` | Outbound calls via Twilio |

### Observability

Every micro-action during execution is recorded as a `RunStep`:

| Step Type | When Recorded |
|-----------|---------------|
| `expert_task` | Expert begins/completes a task |
| `tool_call` | Tool executed with input/output |
| `searching` | Scout phase exploration |
| `analyzing` | Gap check audit |
| `synthesis` | Synthesis phase |
| `writing` | Report generation |
| `error` | Any failure during execution |

RunSteps include correlation IDs, parent-child relationships, token counts, duration, and truncated input/output summaries. This enables full execution replay and debugging.

### State Machine

Mission runs follow a strict state machine with validated transitions:

```
created ──> queued ──> running ──> completed
                         |
                         +──> partially_failed ──> completed
                         |                    +──> failed
                         +──> retrying ──> running
                         |
                         +──> failed
                         |
                         +──> cancelled
```

Every transition is persisted with timestamp and reason. Idempotency keys prevent duplicate execution. Failure categories (`transient`, `model_error`, `rate_limited`, `timeout`, `validation`, `internal`) enable targeted retry logic.

---

## Data Model

### Core Entities

```
Project (scoping container)
  └── Mission (research task)
        ├── AgentCrew (selected experts)
        ├── MissionRun (execution instance)
        │     ├── CrewTask (per-expert task)
        │     │     └── RunStep (micro-action trace)
        │     └── CrewRun (crew execution record)
        ├── Finding (discovered data point)
        └── Report (synthesized output)

Finding
  ├── type: fact | insight | statistic | contact_info | trend | risk | opportunity | ...
  ├── source: web | voice_call | api | public_record | inferred
  ├── confidence: 0.0 - 1.0
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

API docs at `http://localhost:8000/docs`.

---

## Environment Variables

| Variable | Required | Purpose |
|---|:---:|---|
| `GEMINI_API_KEY` | Yes | Core LLM for reasoning, tool-calling, and synthesis |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Celery broker + pub/sub |
| `QDRANT_URL` | Yes | Vector search backend |
| `EXA_API_KEY` | Optional | Exa neural web search and contact discovery |
| `TWILIO_ACCOUNT_SID` | Optional | Outbound voice calling |
| `TWILIO_AUTH_TOKEN` | Optional | Voice call authentication |
| `TWILIO_FROM_NUMBER` | Optional | Voice caller ID |
| `RESEND_API_KEY` | Optional | Email delivery |

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
│   │   │   ├── crews/        # DeerFlow execution engine
│   │   │   │   ├── crew_runner.py      # 5-phase execution orchestrator
│   │   │   │   ├── crew_service.py     # Crew assembly + expert selection
│   │   │   │   ├── task_planner.py     # Gemini-powered task decomposition
│   │   │   │   ├── expert_registry.py  # 10 builtin expert agents
│   │   │   │   └── tool_registry.py    # Agentic tool dispatch
│   │   │   ├── research/     # Deep research engine (Gemini + Exa)
│   │   │   ├── intelligence/  # Signals, insights, recommendations
│   │   │   ├── reports/       # Report generation + export
│   │   │   ├── workflow/      # DAG-based workflow execution
│   │   │   ├── voice/         # Voice call orchestration
│   │   │   └── state_machine.py  # Run lifecycle management
│   │   ├── tasks/            # Celery async tasks (6 queues)
│   │   ├── core/             # Logging, events, rate limiting, WebSocket
│   │   ├── providers/        # LLM provider integrations
│   │   └── prompts/          # System prompts for expert agents
│   ├── alembic/              # Database migrations
│   └── tests/                # pytest test suite
├── dashboard/
│   ├── app/                  # Next.js 14 App Router (28 routes)
│   ├── components/           # Reusable UI components
│   └── lib/                  # API client, types, hooks
├── docker-compose.yml
└── README.md
```

---

**MIT License** — Built by [Madhav Chauhan](https://github.com/madhavcodez)
