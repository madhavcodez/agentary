# AGENTARY IMPLEMENTATION BLUEPRINT

**Version:** 1.0
**Created:** 2026-03-26
**Status:** ALL PHASES COMPLETE (2026-03-26) — Phase 1 + Phase 2 + Phase 3
**Role:** Living reference document. Update checkboxes and status as implementation proceeds.

---

## WORKFLOW

This document is the single source of truth for implementation across Phases 1-3.

**How to use this document:**

1. Before starting any epic, read the relevant section completely
2. Work epic by epic, workstream by workstream, in dependency order
3. After completing each checkbox item, edit this document to mark it `[x]`
4. After completing each epic, update the epic status to COMPLETE
5. Before moving to the next phase, verify against the Readiness Rubric (Section 9)
6. If the plan changes during implementation, update this document first — do not silently diverge

**Execution cadence:**
- Start each work session by reading the current phase section
- End each work session by updating checkboxes and noting blockers
- Never move to Phase N+1 until the Phase N readiness rubric is green

---

## TABLE OF CONTENTS

1. [Executive Framing](#1-executive-framing)
2. [North Star Architecture](#2-north-star-architecture)
3. [Phase 1: Production Trust](#3-phase-1-production-trust-and-platform-hardening)
4. [Phase 2: System of Intelligence](#4-phase-2-vertical-system-of-intelligence)
5. [Phase 3: Closed-Loop Action](#5-phase-3-closed-loop-action)
6. [Data Model Evolution](#6-data-model-evolution)
7. [API and Worker Design](#7-api-and-worker-design)
8. [Frontend / UX Plan](#8-frontend--ux-plan)
9. [Reliability and Eval Framework](#9-reliability-and-eval-framework)
10. [Readiness Rubric](#10-readiness-rubric)
11. [Final Recommendations](#11-final-recommendations)
12. [Key Questions Answered](#12-key-questions-answered)

---

## 1. EXECUTIVE FRAMING

Agentary is an autonomous research and intelligence platform. It already has ambitious scope: agent crews, workflows, voice extraction, monitors, reports, 10+ connectors, real-time feeds, and a full dashboard. The problem is not lack of capability — it is that the system is a sophisticated prototype, not yet a trustworthy operating system.

**The strategy across three phases:**

**Phase 1 — Production Trust.** Make what exists reliable. Every run should have a visible lifecycle. Failures should be diagnosable. Workers should be durable. The live UI should reflect reality. Tests should catch regressions. Stubs should be closed. This phase adds almost no new product scope — it makes the current system real.

**Phase 2 — System of Intelligence.** Transform isolated outputs (findings, reports, transcripts) into a persistent intelligence layer. Introduce typed domain objects: Signal, Observation, Evidence, Insight, Recommendation. All product surfaces — missions, workflows, monitors, voice, reports — feed the same shared graph. Users see living context, not one-off results.

**Phase 3 — Closed-Loop Action.** Turn intelligence into bounded operations. Recommendations become actionable. Policies gate what can auto-execute vs. what needs approval. Outcomes feed back into the intelligence layer. An operator console surfaces pending approvals, failures, and escalations. The platform becomes an operating system for the vertical, not just an analytics dashboard.

**What is intentionally deferred:** CRM ontology (lead/account/opportunity), multi-team workspaces, external enterprise integrations (HubSpot, Salesforce, Calendly), agent marketplace, public API platform. Phase 3's action architecture is designed to plug into these later without rewrite.

---

## 2. NORTH STAR ARCHITECTURE

### Target State After Phase 3

```
                        +-----------------------+
                        |    OPERATOR CONSOLE   |
                        | approvals / queues /  |
                        | escalations / health  |
                        +-----------+-----------+
                                    |
+-----------------------------------+-----------------------------------+
|                        DASHBOARD (Next.js 14)                         |
|  Entity pages | Signal feed | Recommendation inbox | Review queue     |
|  Mission live | Workflow editor | Reports | Voice | Monitors          |
+-----------------------------------+-----------------------------------+
                                    |
                            REST + WebSocket
                                    |
+-------------------------------------------------------------------+
|                        API LAYER (FastAPI)                         |
+-----------+----------+-----------+-----------+--------------------+
|  Run      | Signal   | Evidence  | Action    | Policy             |
|  Engine   | Pipeline | Store     | Engine    | Engine             |
+-----------+----------+-----------+-----------+--------------------+
|                                                                   |
|                    INTELLIGENCE LAYER                              |
|  Entity + Relationship + Signal + Observation + Evidence +        |
|  Insight + Recommendation + ActionRequest + ActionOutcome         |
|                                                                   |
+-----------+----------+-----------+-----------+--------------------+
|                    EXECUTION LAYER                                 |
|  CrewRunner | WorkflowExecutor | VoicePipeline | MonitorService   |
|  Connectors (10+) | Tool Registry | Gemini 2.5 Flash             |
+-----------+----------+-----------+-----------+--------------------+
|                    INFRASTRUCTURE                                  |
|  PostgreSQL | Redis | Qdrant | Celery | APScheduler | Nginx       |
+-----------+----------+-----------+-----------+--------------------+
```

### How Phases Evolve Into This

| Layer | Phase 1 | Phase 2 | Phase 3 |
|-------|---------|---------|---------|
| Execution | Harden (state machines, retries, idempotency) | Execution feeds Signal pipeline | Execution triggers Actions |
| Intelligence | N/A (existing Finding model stays) | New: Signal, Observation, Evidence, Insight, Recommendation | Recommendation -> ActionRequest |
| Action | N/A | N/A | New: ActionRequest, Policy, Approval, ActionExecution, ActionOutcome |
| Frontend | Fix real-time, close stubs | Entity pages, signal feed, recommendation inbox | Operator console, approval flows |
| Observability | Structured logs, run traces, correlation IDs | Provenance visible in UI | Action audit trail |

---

## 3. PHASE 1: PRODUCTION TRUST AND PLATFORM HARDENING

**Status:** COMPLETE (2026-03-26)

### Objective

Turn the platform from "promising prototype" into a stable execution system. No new product scope. Make the core system real.

### User Outcomes

- Every run has a visible lifecycle — no "mystery stuck" states
- Failures are understandable with categorized reasons and step history
- Live UI reflects actual backend state via WebSocket (not polling)
- No exposed stubs or broken paths on core user flows
- Workers and queues behave predictably under load

### Non-Goals

- New product features
- New domain models beyond what's needed for run lifecycle
- CRM concepts
- Enterprise admin
- New connectors
- New agent types

---

### EPIC 1.1: Run Lifecycle State Machine
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES — blocks all other epics

Every execution type needs a formal state machine with transition tracking.

**Canonical states:**

```
created -> queued -> running -> completed
                  |         |-> partially_failed -> completed
                  |         |-> failed
                  |         |-> cancelled
                  |-> retrying -> running
                  |-> awaiting_input -> running
```

**Failure categories (new enum):**

| Category | Description | Retryable |
|----------|-------------|-----------|
| `transient_connector` | External API timeout/5xx | Yes (up to 3) |
| `model_error` | Gemini returned error/empty | Yes (up to 2) |
| `rate_limited` | External API rate limit | Yes (with backoff) |
| `timeout` | Task exceeded time limit | Yes (once) |
| `validation` | Input/output schema invalid | No |
| `internal` | Bug/unexpected exception | No |
| `cancelled` | User or system cancelled | No |

**Implementation tasks:**

- [ ] Create `backend/app/models/enums.py` with `RunStatus`, `FailureCategory` enums shared across all run types
- [ ] Create `backend/app/services/state_machine.py` — generic state machine enforcing valid transitions
  - Accepts: current_state, target_state
  - Returns: new_state or raises InvalidTransition
  - Logs every transition with timestamp
- [ ] Add to `MissionRun` model: `failure_category`, `failure_message`, `state_transitions` (JSONB array of `{from, to, timestamp, reason}`), `retry_count`, `max_retries`, `correlation_id`
- [ ] Add same fields to `CrewRun`, `WorkflowRun`, `CallRecord` (voice runs), `Report` (report generation runs)
- [ ] Add `MonitorRun` model (currently monitors don't track individual check runs)
- [ ] Create Alembic migration for all schema changes
- [ ] Update `CrewRunner.execute_run()` to use state machine (replace raw status string assignments at lines ~71-78)
- [ ] Update workflow executor to use state machine
- [ ] Update voice service to use state machine
- [ ] Update report generator to use state machine
- [ ] Update monitor service to use state machine
- [ ] Every status change emits an event via EventBus

---

### EPIC 1.2: Durable Orchestration
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

**Implementation tasks:**

- [ ] Complete `/api/missions/{mission_id}/run` endpoint — wire Celery dispatch (currently TODO)
- [ ] Add `idempotency_key` column to `MissionRun`, `CrewRun`, `WorkflowRun`
  - Generated at dispatch time: `f"{run_type}:{entity_id}:{uuid4()}"`
  - Celery tasks check for existing completed run with same key before executing
- [ ] Add `correlation_id` (UUID) propagated through: HTTP request -> Celery task -> CrewRunner -> tool calls -> events
  - Set via middleware on incoming requests
  - Passed as Celery task kwarg
  - Included in all Event emissions
  - Included in all log entries
- [ ] Configure Celery dead-letter queue:
  - Add `task_reject_on_worker_lost = True`
  - Add `task_acks_late = True` for at-least-once delivery
  - Route failed tasks (after max retries) to `dead_letter` queue
  - Add `/api/admin/dead-letter` endpoint to inspect failed tasks
- [ ] Add step-level checkpointing to `CrewRunner`:
  - After each expert completes, persist `CrewTask` with output before moving to next phase
  - On resume/retry, skip already-completed tasks
  - Track `last_completed_step` on `CrewRun`
- [ ] Add bounded retry logic to connector calls:
  - `transient_connector`: retry 3x with exponential backoff (1s, 4s, 16s)
  - `model_error`: retry 2x with 2s delay
  - `rate_limited`: retry 3x with backoff starting at rate-limit header value or 30s
  - All other categories: no retry, fail immediately
- [ ] Ensure one connector timeout does not poison entire run:
  - Wrap each expert task execution in try/except
  - Individual task failure marks that task as `failed` but run continues
  - Run status becomes `partially_failed` if some tasks failed but others completed
- [ ] Add `timeout_seconds` to `CrewTask` model (default 300s per task, 3600s per run)
  - Celery `soft_time_limit` already set to 3600 — add per-task timeout via asyncio.wait_for

---

### EPIC 1.3: Real-Time UX
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

**Current state:** WebSocket manager + Redis bridge exist and work. Frontend pages use 2-5s polling instead of connecting to the socket.

**WebSocket Event Contract (typed):**

Every WebSocket message follows this schema:

```typescript
interface WSEvent {
  event_type: string;          // e.g. "mission.started", "agent.thinking"
  correlation_id: string;      // traces back to the run
  project_id: string | null;
  mission_id: string | null;
  run_id: string | null;
  data: Record<string, any>;   // event-specific payload
  timestamp: string;           // ISO 8601
}
```

**Implementation tasks:**

- [ ] Add `correlation_id` and `run_id` fields to `Event` class in `backend/app/core/events.py`
- [ ] Add new event types to `EventType` enum:
  - `run.state_changed` (for all run types)
  - `run.step_completed`
  - `run.retrying`
  - `workflow.node_started`, `workflow.node_completed`, `workflow.node_failed`
  - `voice.call_ringing`, `voice.call_transcript_ready`
  - `monitor.check_started`, `monitor.check_completed`
- [ ] Create `dashboard/lib/types/events.ts` — TypeScript types matching backend Event schema
- [ ] Refactor `dashboard/lib/hooks/useWebSocket.ts`:
  - Auto-connect on mount with auth token
  - Auto-reconnect with exponential backoff (1s, 2s, 4s, max 30s)
  - Parse incoming messages into typed WSEvent objects
  - Expose `subscribe(eventType, handler)` API
  - Track connection state (connecting, connected, disconnected, reconnecting)
  - Show connection indicator in UI
- [ ] Convert `dashboard/app/missions/[missionId]/page.tsx` from polling to WebSocket:
  - Subscribe to `agent.*`, `mission.*`, `finding.*`, `run.*` events filtered by mission_id
  - Remove setInterval polling
  - Keep polling as fallback if WS fails to connect (degrade gracefully)
- [ ] Convert `dashboard/app/workflows/[id]/page.tsx` workflow run view from polling to WebSocket
- [ ] Convert `dashboard/app/dashboard/page.tsx` command center from polling to WebSocket
- [ ] Convert `dashboard/app/voice/` pages from polling to WebSocket
- [ ] Add WebSocket connection status indicator to Nav component (green dot = connected, yellow = reconnecting, red = disconnected)
- [ ] Ensure UI never shows stale state:
  - On reconnect, fetch latest state via REST then apply subsequent WS events
  - Timestamp-based dedup to prevent out-of-order events from causing UI regression

---

### EPIC 1.4: Observability
**Status:** COMPLETE (2026-03-26)
**Critical path:** NO (but blocks production confidence)

**Implementation tasks:**

- [ ] Create `backend/app/core/logging_config.py`:
  - Structured JSON logging (not plain text)
  - Include: timestamp, level, correlation_id, user_id, module, message, extra
  - Configure on app startup in main.py
- [ ] Create `backend/app/core/correlation.py`:
  - Middleware that generates/extracts correlation_id per request
  - Stores in contextvars for access anywhere in the call stack
  - Passes to Celery tasks via headers
- [ ] Create `RunStep` model (`backend/app/models/run_step.py`):
  ```
  id: UUID
  run_id: UUID (FK to mission_runs / crew_runs / workflow_runs — polymorphic)
  run_type: Enum (mission, crew, workflow, voice, monitor, report)
  step_type: Enum (expert_task, tool_call, synthesis, node_execution, api_call)
  step_name: String
  status: RunStatus
  input_summary: JSONB (truncated input — NOT full prompt)
  output_summary: JSONB (truncated output)
  error: JSONB
  tokens_used: Integer
  cost_usd: Float
  duration_ms: Integer
  started_at: DateTime
  completed_at: DateTime
  ```
- [ ] Emit RunStep records from CrewRunner (one per expert task, one per tool call)
- [ ] Emit RunStep records from WorkflowExecutor (one per node)
- [ ] Emit RunStep records from VoiceService (one per call)
- [ ] Add `/api/runs/{run_id}/steps` endpoint to fetch run trace
- [ ] Add token/cost accounting:
  - Track tokens_used and estimated cost per RunStep
  - Aggregate on CrewRun/MissionRun
  - Show in mission detail UI
- [ ] Enhance `/health` endpoint:
  - Add Celery worker count + queue depths (research, voice, monitors, reports)
  - Add last 5min error rate per connector
  - Add average run duration by type
- [ ] Add run trace view to mission detail page (collapsible timeline of RunSteps)

---

### EPIC 1.5: Close Trust Blockers (Stubs)
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

**Implementation tasks:**

- [ ] **Complete mission /run dispatch** (`backend/app/api/missions.py`):
  - Wire `POST /api/missions/{mission_id}/run` to dispatch `plan_and_start_mission` Celery task
  - Create MissionRun record with idempotency_key
  - Return 202 Accepted with run_id
- [ ] **Complete call post-processing** (`backend/app/services/voice/call_post_processor.py` line 44):
  - Integrate Gemini for: outcome classification, call quality scoring, summary generation
  - Extract structured data points from transcript
  - Update CallRecord with extracted_data, sentiment, call_quality_score
- [ ] **Complete Python executor** (`backend/app/services/data_sources/connectors/python_executor.py`):
  - Implement remaining NotImplementedError methods
  - Add sandboxing (restricted builtins, no file/network access)
  - Add execution timeout (30s default)
  - Add output size limit (1MB)
- [ ] **Build voice extraction detail page** (`dashboard/app/voice/extractions/[id]/page.tsx`):
  - Session overview (name, status, progress bar)
  - Call list with status badges (pending/ringing/connected/completed/failed)
  - Click call -> transcript + extracted data
  - Start/stop call buttons
  - Batch execute button
- [ ] **Fix monitoring edge cases** (`backend/app/services/monitors/monitor_service.py`):
  - Handle monitor target unreachable (don't create false-positive alerts)
  - Handle monitor check timeout (separate from "no change detected")
  - Deduplicate alerts for same condition within cooldown period
  - Add `last_error` field to Monitor model

---

### EPIC 1.6: Testing
**Status:** COMPLETE (2026-03-26)
**Critical path:** NO (but blocks Phase 1 readiness)

**Test Pyramid:**

| Level | Target Coverage | Framework | What to Test |
|-------|----------------|-----------|-------------|
| Unit | 80%+ of services | pytest | State machine transitions, validators, connector wrappers, scoring logic, schema parsing |
| Integration | Critical paths | pytest + testcontainers | Worker+Redis+DB, workflow multi-node, monitor pipeline, voice extraction flow, report generation |
| E2E | 4 golden paths | Playwright | Mission flow, workflow flow, monitor flow, voice flow |
| Frontend Unit | Key components | Vitest + Testing Library | WebSocket hook, API client, critical UI components |

**Implementation tasks:**

- [ ] **State machine unit tests** (`backend/tests/test_state_machine.py`):
  - Valid transitions succeed
  - Invalid transitions raise
  - Transition history is recorded
  - All failure categories are handled
- [ ] **CrewRunner integration test** (`backend/tests/integration/test_crew_runner.py`):
  - Mock Gemini responses
  - Verify parallel execution
  - Verify finding creation
  - Verify state transitions through lifecycle
  - Verify partial failure handling
- [ ] **Workflow integration test** (`backend/tests/integration/test_workflow_flow.py`):
  - Create workflow with 3 nodes
  - Execute run
  - Verify node execution order (topological)
  - Verify run status transitions
- [ ] **Monitor integration test** (`backend/tests/integration/test_monitor_flow.py`):
  - Create monitor
  - Trigger check
  - Verify alert creation
  - Verify alert deduplication
- [ ] **Voice integration test** (`backend/tests/integration/test_voice_flow.py`):
  - Create extraction session
  - Plan calls
  - Simulate call completion
  - Verify transcript extraction
  - Verify data extraction
- [ ] **Set up frontend testing** (`dashboard/`):
  - Install vitest, @testing-library/react, jsdom
  - Create `vitest.config.ts`
  - Create `dashboard/__tests__/hooks/useWebSocket.test.ts`
  - Create `dashboard/__tests__/lib/api.test.ts`
  - Create `dashboard/__tests__/components/LiveActivityFeed.test.tsx`
- [ ] **E2E golden path: Mission** (`tests/e2e/test_mission_flow.py`):
  - Register user -> create project -> create mission -> start -> verify live events -> verify findings -> generate report
- [ ] **E2E golden path: Workflow** (`tests/e2e/test_workflow_flow.py`):
  - Create workflow -> add nodes -> validate -> run -> verify node execution -> verify run history
- [ ] **CI pipeline** (GitHub Actions or similar):
  - Run unit tests on every push
  - Run integration tests on PR
  - Run E2E tests before merge to main
  - Fail build on test failure

---

### Phase 1 Acceptance Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| Run reliability | % of valid runs completing without manual intervention | >95% |
| Retry handling | Transient errors auto-retried | 100% of retryable categories |
| Live UI | Core run pages use WebSocket, not polling | Mission, workflow, dashboard, voice |
| Debuggability | Failed runs have inspectable reason + step history | 100% of failures |
| State machine | All run types use formal lifecycle | MissionRun, CrewRun, WorkflowRun, CallRecord, Report, MonitorRun |
| Testing | Critical paths covered in CI | 4 integration tests + 4 E2E golden paths |
| Stubs closed | No exposed partial features on core paths | 0 user-visible TODOs |
| Observability | Structured logs with correlation IDs | Every request/task/event |

---

## 4. PHASE 2: VERTICAL SYSTEM OF INTELLIGENCE

**Status:** COMPLETE (2026-03-26)
**Prerequisite:** Phase 1 readiness rubric is GREEN

### Objective

Transform the platform from "agent runner that produces reports" into a persistent intelligence layer. The system should maintain living context — entities with histories, signals with provenance, evidence-backed recommendations — not just one-off outputs.

### User Outcomes

- Open an entity page and see one coherent truth surface: what we know, when we learned it, how fresh it is, what changed
- A recommendation inbox that says "investigate X" with linked evidence, confidence score, freshness, and source chain
- Monitors, missions, workflows, and voice extraction all feed the same intelligence graph
- Users understand "what changed / why it matters / what to do next" from core screens

### Non-Goals

- CRM objects (lead, account, opportunity, pipeline stages)
- Enterprise admin / team workspaces
- External system sync
- Public API

---

### EPIC 2.1: Intelligence Domain Model
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES — blocks all Phase 2 work

**New models to create:**

**Signal** — Any event or change worth reasoning about.

```
id: UUID
project_id: UUID (FK)
source_type: Enum (monitor, mission, workflow, voice, user, api, upload)
source_id: UUID (the run/monitor/etc that produced it)
signal_type: Enum (change_detected, data_extracted, threshold_breached,
                   pattern_found, anomaly_detected, user_flagged)
title: String
content: Text
structured_data: JSONB
entity_id: UUID (FK, nullable — linked entity if resolved)
confidence: Float
is_processed: Boolean (has this been turned into observations/evidence?)
expires_at: DateTime (nullable — for time-sensitive signals)
created_at: DateTime
```

**Observation** — A structured record extracted from a signal or run.

```
id: UUID
project_id: UUID (FK)
entity_id: UUID (FK, nullable)
signal_id: UUID (FK, nullable — the signal that produced this)
run_id: UUID (nullable — the run that produced this)
observation_type: Enum (fact, measurement, quote, classification,
                        comparison, temporal_change, relationship)
subject: String
content: Text
structured_value: JSONB (the typed data)
source_type: SourceType (web, voice_call, api, etc.)
source_url: String
source_name: String
observed_at: DateTime (when the observation was made in the real world)
confidence: Float
is_stale: Boolean (computed from freshness rules)
created_at: DateTime
```

**Evidence** — Links an observation to an insight or recommendation.

```
id: UUID
observation_id: UUID (FK)
insight_id: UUID (FK, nullable)
recommendation_id: UUID (FK, nullable)
evidence_type: Enum (supporting, contradicting, contextual)
weight: Float (how strongly this evidence supports/contradicts)
notes: Text (optional explanation)
created_at: DateTime
```

**Insight** — A synthesized understanding derived from multiple observations.

```
id: UUID
project_id: UUID (FK)
entity_id: UUID (FK, nullable)
insight_type: Enum (trend, risk, opportunity, anomaly, summary, comparison)
title: String
content: Text
structured_data: JSONB
confidence: Float
freshness_at: DateTime (last time evidence was refreshed)
staleness_threshold_hours: Integer (default 168 = 1 week)
is_stale: Boolean (computed)
is_active: Boolean
superseded_by: UUID (FK, self — for updated insights)
created_at: DateTime
updated_at: DateTime
```

**Recommendation** — An actionable suggestion with confidence and evidence.

```
id: UUID
project_id: UUID (FK)
entity_id: UUID (FK, nullable)
insight_id: UUID (FK, nullable — the insight that triggered this)
recommendation_type: Enum (investigate, monitor, contact, update, review, escalate)
title: String
rationale: Text (why this is recommended)
suggested_action: JSONB (structured: {action_type, parameters})
confidence: Float
priority: Enum (critical, high, medium, low)
status: Enum (pending, accepted, rejected, expired, acted_on)
reviewed_by: UUID (FK to users, nullable)
reviewed_at: DateTime
expires_at: DateTime (nullable)
created_at: DateTime
```

**EntityAlias** — Source-specific identifiers for entities.

```
id: UUID
entity_id: UUID (FK)
alias_type: Enum (name_variant, external_id, url, phone, email, address)
alias_value: String
source_name: String
confidence: Float
created_at: DateTime
```

**Relationship** — Typed connections between entities.

```
id: UUID
project_id: UUID (FK)
from_entity_id: UUID (FK)
to_entity_id: UUID (FK)
relationship_type: Enum (subsidiary_of, competitor_of, partner_of,
                          located_at, works_at, supplies_to, related_to)
properties: JSONB
confidence: Float
source_id: UUID (nullable — what produced this relationship)
created_at: DateTime
```

**Implementation tasks:**

- [ ] Create all 7 model files in `backend/app/models/`
- [ ] Create Alembic migration
- [ ] Add relationships to existing Entity model (aliases, relationships, observations, insights)
- [ ] Create Pydantic schemas for all new models in `backend/app/schemas/`
- [ ] Create `backend/app/services/intelligence/` directory with:
  - `signal_service.py` — ingest, deduplicate, route signals
  - `observation_service.py` — extract observations from signals/findings
  - `evidence_service.py` — link observations to insights/recommendations
  - `insight_service.py` — synthesize insights from observations
  - `recommendation_service.py` — generate and score recommendations
  - `freshness_service.py` — compute staleness, trigger refresh

---

### EPIC 2.2: Signal Pipeline
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

All existing product surfaces must feed into the Signal pipeline.

**Signal sources and mapping:**

| Source | Trigger | Signal Type | Data |
|--------|---------|-------------|------|
| Monitor check | Alert created | `change_detected` or `threshold_breached` | Monitor config + detected change |
| Mission finding | Finding created | `data_extracted` or `pattern_found` | Finding data |
| Voice transcript | Call completed | `data_extracted` | Extracted data + transcript |
| Workflow output | Node completed | Varies by node type | Node output |
| User action | Manual flag | `user_flagged` | User annotation |

**Implementation tasks:**

- [ ] Create signal emission hooks in existing services:
  - `CrewRunner` — after finding creation, emit `data_extracted` signal
  - `MonitorService` — after alert creation, emit `change_detected` signal
  - `VoiceService` — after extraction, emit `data_extracted` signal
  - `WorkflowExecutor` — after node completion, emit signal based on node type
- [ ] Create `SignalProcessor` Celery task:
  - Receives raw signal
  - Deduplicates (same source + same content hash within 1 hour = skip)
  - Attempts entity resolution (link signal to existing entity if possible)
  - Extracts observations (via Gemini structured output)
  - Links observations to existing insights if relevant
  - Queues for insight generation if enough new observations accumulate
- [ ] Add `signals` Celery queue and task routing
- [ ] Create `/api/signals` endpoints:
  - `GET /api/signals` — list signals (filterable by project, entity, type, date range)
  - `GET /api/signals/{signal_id}` — signal detail with linked observations
  - `POST /api/signals` — manually create signal (user-flagged)

---

### EPIC 2.3: Finding-to-Observation Migration
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

The existing `Finding` model needs to bridge into the new intelligence model without breaking existing functionality.

**Strategy:** Finding remains as-is (backward compatible). A post-processing step converts Findings into Observations. New code writes Observations directly.

**Implementation tasks:**

- [ ] Create `FindingToObservationAdapter` service:
  - Maps Finding fields to Observation fields
  - Creates Evidence links
  - Resolves entity references from `Finding.entity_refs` JSONB
- [ ] Run migration job for existing findings -> observations (idempotent, skips already-migrated)
- [ ] Update CrewRunner to emit both Finding (backward compat) and Observation (new path)
- [ ] Add `observation_id` FK to Finding model (links finding to its derived observation)

---

### EPIC 2.4: Entity Resolution Enhancement
**Status:** COMPLETE (2026-03-26)
**Critical path:** NO (but high value)

**Implementation tasks:**

- [ ] Add `EntityAlias` model and migration
- [ ] Update `entity_service.py`:
  - `find_or_create` checks aliases before creating new entity
  - Alias matching: exact match on external_id/email/phone, fuzzy on name variants
  - Confidence-based merge: auto-merge above 0.9, queue for review 0.7-0.9, skip below 0.7
- [ ] Add `Relationship` model and migration
- [ ] Create relationship extraction:
  - After observations are created, use Gemini to identify entity relationships
  - Store as Relationship records
- [ ] Add merge review queue:
  - `GET /api/entities/merge-candidates` — pairs above 0.7 confidence
  - `POST /api/entities/merge` — execute merge (already exists, enhance with undo)
  - `POST /api/entities/merge/{merge_id}/undo` — reverse a merge
  - Store merge history for reversibility

---

### EPIC 2.5: Insight and Recommendation Generation
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

**Implementation tasks:**

- [ ] Create `InsightGenerator` service:
  - Triggered when entity accumulates N+ new observations since last insight refresh
  - Uses Gemini structured output to synthesize observations into insights
  - Links evidence (Observation -> Evidence -> Insight)
  - Computes confidence as weighted average of evidence confidences
  - Sets freshness_at to now
- [ ] Create `RecommendationGenerator` service:
  - Triggered after insight generation
  - Uses insights + entity context to generate recommendations
  - Each recommendation has: type, rationale, suggested_action, confidence, priority
  - Links to supporting insight and evidence
- [ ] Create freshness service:
  - Nightly Celery Beat task: mark insights as stale if `freshness_at + staleness_threshold_hours < now`
  - Stale insights trigger "refresh recommended" in UI
  - Option to auto-trigger monitor/mission re-run for stale entities
- [ ] Create `/api/insights` endpoints:
  - `GET /api/insights` — list (filterable by project, entity, type, staleness)
  - `GET /api/insights/{insight_id}` — detail with evidence chain
- [ ] Create `/api/recommendations` endpoints:
  - `GET /api/recommendations` — list (filterable by project, entity, type, status, priority)
  - `PUT /api/recommendations/{id}/accept` — mark accepted
  - `PUT /api/recommendations/{id}/reject` — mark rejected with reason
  - `GET /api/recommendations/inbox` — pending recommendations sorted by priority

---

### EPIC 2.6: Intelligence Frontend
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

**New/enhanced pages:**

- [ ] **Entity Detail Page** (`dashboard/app/entities/[id]/page.tsx`):
  - Entity header (name, type, verified badge, confidence, last updated)
  - Aliases section (all known identifiers)
  - Relationships graph (simple list, not full graph viz)
  - Timeline: observations sorted by date with source icons
  - Active insights with evidence expandable
  - Recommendations for this entity
  - Related reports and missions
- [ ] **Signal Feed** (`dashboard/app/signals/page.tsx`):
  - Chronological feed of signals
  - Filter by: source type, signal type, entity, date range
  - Click signal -> see linked observations and entity
  - WebSocket-driven (new signals appear in real-time)
- [ ] **Recommendation Inbox** (`dashboard/app/recommendations/page.tsx`):
  - List of pending recommendations sorted by priority
  - Each card: title, entity, confidence badge, freshness indicator, evidence count
  - Accept / Reject buttons with reason modal
  - Click -> full recommendation detail with evidence chain and provenance
- [ ] **Enhanced Entity List** (`dashboard/app/entities/page.tsx`):
  - Add: observation count, insight count, staleness indicator
  - Add: merge candidates badge
  - Filter by: type, staleness, has-recommendations
- [ ] **Freshness indicators across UI**:
  - Green: fresh (within threshold)
  - Yellow: aging (>50% of threshold)
  - Red: stale (exceeded threshold)
  - Show on: entity pages, insights, recommendations, findings

---

### Phase 2 Acceptance Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| Unified model | All run outputs land in shared intelligence graph | Missions, monitors, voice, workflows all produce Signals/Observations |
| Evidence | Every insight has source-backed provenance | 100% of generated insights |
| Freshness | Insights show when last refreshed | Freshness indicator on all insights |
| Entity quality | Merge candidates surfaced for review | Auto-merge >0.9, review queue 0.7-0.9 |
| Recommendations | Generated from insights with confidence | At least 1 recommendation type working |
| Frontend | Entity detail, signal feed, recommendation inbox exist | 3 new pages functional |
| Convergence | Multiple product surfaces feed same graph | 4+ signal sources active |

---

## 5. PHASE 3: CLOSED-LOOP ACTION

**Status:** COMPLETE (2026-03-26)
**Prerequisite:** Phase 2 readiness rubric is GREEN

### Objective

Turn intelligence into bounded operations. Recommendations become actionable with policy-gated approval. Outcomes feed back into the intelligence layer. An operator console surfaces the operational state of the system.

### User Outcomes

- Recommendations come with "take action" buttons
- Low-risk actions auto-execute (e.g., update internal status, send alert)
- High-risk actions queue for approval with evidence view
- Outcomes update the intelligence layer (accepted recommendation -> higher entity confidence)
- An operator can manage the whole system from one console

### Non-Goals

- CRM-specific actions
- External system integrations (HubSpot, Salesforce)
- Multi-team role-based permissions
- Public-facing action APIs

---

### EPIC 3.1: Action Domain Model
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

**New models:**

**ActionRequest** — A proposed action with evidence.

```
id: UUID
project_id: UUID (FK)
recommendation_id: UUID (FK, nullable)
entity_id: UUID (FK, nullable)
user_id: UUID (FK — who/what created this)
action_type: Enum (update_status, send_alert, trigger_workflow, trigger_monitor,
                   create_task, generate_report, send_digest, queue_call,
                   merge_entities, escalate, custom)
title: String
description: Text
parameters: JSONB (action-specific config)
confidence: Float (from recommendation or manual=1.0)
priority: Enum (critical, high, medium, low)
requires_approval: Boolean (computed from policy)
status: Enum (pending_approval, approved, rejected, executing, completed,
              failed, cancelled, expired)
state_transitions: JSONB (array of {from, to, timestamp, actor_id, reason})
policy_id: UUID (FK, nullable — which policy determined approval requirement)
approved_by: UUID (FK, nullable)
approved_at: DateTime
expires_at: DateTime (nullable)
created_at: DateTime
```

**ActionPolicy** — Rules governing action autonomy.

```
id: UUID
user_id: UUID (FK)
project_id: UUID (FK, nullable — null = global for user)
name: String
description: Text
rules: JSONB (array of {condition, result})
  condition: {action_type, confidence_above, priority_in, entity_type_in}
  result: {auto_approve: bool, require_approval: bool, escalate_to: UUID, timeout_hours: int}
is_active: Boolean
priority: Integer (higher = evaluated first)
created_at: DateTime
updated_at: DateTime
```

**ActionExecution** — What happened when the action ran.

```
id: UUID
action_request_id: UUID (FK)
executor_type: Enum (system, celery_worker, external)
started_at: DateTime
completed_at: DateTime
status: Enum (running, completed, failed, rolled_back)
result: JSONB (what happened)
error: JSONB (if failed)
side_effects: JSONB (what was changed — for rollback reference)
```

**ActionOutcome** — The result feeding back into intelligence.

```
id: UUID
action_request_id: UUID (FK)
execution_id: UUID (FK)
outcome_type: Enum (success, partial_success, failure, rejected_by_user,
                     no_effect, needs_followup)
impact: JSONB (what changed in the intelligence layer)
feedback_signal_id: UUID (FK to Signal, nullable — the signal created by this outcome)
notes: Text
created_at: DateTime
```

**Implementation tasks:**

- [ ] Create all 4 model files
- [ ] Create Alembic migration
- [ ] Create Pydantic schemas
- [ ] Create `backend/app/services/actions/` directory with:
  - `action_service.py` — create, approve, reject, execute, cancel
  - `policy_engine.py` — evaluate policies to determine approval requirement
  - `action_executor.py` — dispatch action to appropriate handler
  - `outcome_service.py` — record outcomes, create feedback signals

---

### EPIC 3.2: Policy Engine
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

**Default policies (seeded for every user):**

| Action Type | Default Policy |
|-------------|---------------|
| `update_status` | Auto-approve if confidence > 0.8 |
| `send_alert` | Auto-approve |
| `trigger_workflow` | Require approval |
| `trigger_monitor` | Auto-approve |
| `create_task` | Auto-approve |
| `generate_report` | Auto-approve |
| `send_digest` | Auto-approve |
| `queue_call` | Require approval |
| `merge_entities` | Require approval if confidence < 0.9, else auto |
| `escalate` | Auto-approve |
| `custom` | Require approval |

**Implementation tasks:**

- [ ] Implement `PolicyEngine.evaluate(action_request) -> PolicyDecision`:
  - Load active policies for user/project, sorted by priority
  - Evaluate conditions against action_request fields
  - Return: `{requires_approval, auto_approve, escalate_to, timeout_hours}`
  - If no policy matches, default to require_approval
- [ ] Create seed script for default policies
- [ ] Create `/api/policies` CRUD endpoints (enhance existing)
- [ ] Create policy test suite (unit tests for each default policy)

---

### EPIC 3.3: Action Execution Workers
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

**Implementation tasks:**

- [ ] Create action handlers (one per action type):
  - `UpdateStatusHandler` — updates entity/insight/recommendation status
  - `SendAlertHandler` — sends email/dashboard alert
  - `TriggerWorkflowHandler` — starts workflow run
  - `TriggerMonitorHandler` — triggers monitor check
  - `CreateTaskHandler` — creates internal task
  - `GenerateReportHandler` — triggers report generation
  - `QueueCallHandler` — creates voice extraction call
  - `MergeEntitiesHandler` — executes entity merge
  - `EscalateHandler` — sends escalation notification
- [ ] Create `ActionDispatcher` Celery task:
  - Receives action_request_id
  - Creates ActionExecution record
  - Routes to appropriate handler
  - Records outcome
  - Creates feedback Signal if outcome changes intelligence state
- [ ] Add `actions` Celery queue and routing
- [ ] Create `/api/actions` endpoints:
  - `POST /api/actions` — create action request (triggers policy eval)
  - `GET /api/actions` — list (filterable by status, type, project)
  - `GET /api/actions/{id}` — detail with execution/outcome
  - `PUT /api/actions/{id}/approve` — approve pending action
  - `PUT /api/actions/{id}/reject` — reject with reason
  - `PUT /api/actions/{id}/cancel` — cancel pending/approved action
  - `GET /api/actions/pending` — pending approvals for current user

---

### EPIC 3.4: Approval Workflow UI
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES

**Implementation tasks:**

- [ ] **Approval Inbox** (`dashboard/app/approvals/page.tsx`):
  - List of pending action requests sorted by priority/age
  - Each card: action type icon, title, entity, confidence, evidence count, time pending
  - Bulk approve/reject for low-risk batch
  - Timeout indicator (approaching expiry)
- [ ] **Action Detail Modal/Page**:
  - What: action description and parameters
  - Why: linked recommendation and rationale
  - Evidence: expandable evidence chain from recommendation -> insight -> observations -> sources
  - Confidence: visual confidence meter
  - Approve / Reject / Edit buttons
  - Reject reason textarea
- [ ] **Action History** (`dashboard/app/actions/page.tsx`):
  - Completed/failed/rejected actions
  - Filter by: type, status, date range, entity
  - Click -> execution detail with outcome

---

### EPIC 3.5: Operator Console
**Status:** COMPLETE (2026-03-26)
**Critical path:** NO (high value, can be simplified)

**Implementation tasks:**

- [ ] **Operator Console** (`dashboard/app/operator/page.tsx`):
  - **Pending approvals count** with urgency indicator
  - **Failed actions** (last 24h) with retry buttons
  - **Stale recommendations** that need refresh
  - **Queue health**: Celery queue depths, worker status
  - **Connector health**: circuit breaker states, error rates
  - **Recent escalations**
  - **System alerts**: stuck runs, dead-letter queue items
- [ ] **Action outcome feedback loop**:
  - When action completes, create Signal with `source_type=action_outcome`
  - Signal feeds back into observation/insight pipeline
  - Accepted recommendations boost entity confidence
  - Rejected recommendations trigger review of generating logic

---

### EPIC 3.6: Outcome Feedback Loop
**Status:** COMPLETE (2026-03-26)
**Critical path:** YES (differentiator)

**Implementation tasks:**

- [ ] After ActionExecution completes:
  - Create ActionOutcome record
  - If `outcome_type == success`:
    - Create Signal with `source_type=action_outcome`
    - If action was from recommendation, update recommendation status to `acted_on`
    - If action involved entity, update entity `confidence_score` (+0.05 for success)
  - If `outcome_type == failure`:
    - Log failure details
    - If action was from recommendation, keep recommendation as `pending` for retry
    - Create alert for operator
  - If `outcome_type == rejected_by_user`:
    - Record rejection reason
    - Use rejection as negative feedback for future recommendation scoring
    - Signal with type `user_flagged` feeding back into intelligence
- [ ] Track action utility metrics:
  - Acceptance rate by action type
  - Success rate by action type
  - Average time-to-approve
  - Recommendations that led to successful actions vs. rejected

---

### Phase 3 Acceptance Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| Action model | Separate typed objects for request, policy, execution, outcome | All 4 models exist and functional |
| Safety | Consequential actions gated by policy | 100% of action types have default policy |
| Approval | Pending actions surfaced in UI with evidence | Approval inbox functional |
| Traceability | Every action has provenance, actor, timestamps, result | Full audit trail |
| Feedback loop | Action outcomes create signals feeding intelligence layer | Outcome -> Signal pipeline working |
| Operator UX | Operator console shows system health and pending work | Console with 5+ operational panels |
| Autonomy | Low-risk actions auto-execute per policy | At least 4 action types auto-approve |
| Trust | Users understand why an action was proposed and can undo/reject | Evidence chain visible in approval UI |

---

## 6. DATA MODEL EVOLUTION

### State Machine Diagram (All Run Types)

```
                  ┌──────────┐
                  │ created  │
                  └────┬─────┘
                       │ dispatch()
                  ┌────▼─────┐
                  │ queued   │
                  └────┬─────┘
                       │ worker_picks_up()
                  ┌────▼─────┐     timeout/error
              ┌───│ running  │────────────────┐
              │   └──┬───┬───┘                │
              │      │   │                    │
   needs_input│      │   │ partial_fail  ┌────▼──────┐
              │      │   └──────────────►│ retrying  │
         ┌────▼────────┐                 └────┬──────┘
         │ awaiting_   │                      │
         │ input       │               ┌──────▼──────┐
         └─────┬───────┘               │  running    │
               │ input_received()      │  (retry)    │
               └──────►running         └─────────────┘
                       │
              ┌────────┴────────┐
              │                 │
     ┌────────▼───┐    ┌───────▼──────────┐
     │ completed  │    │ partially_failed │
     └────────────┘    └──────────────────┘
                              │
                       (or if unrecoverable)
                              │
                       ┌──────▼──────┐
                       │   failed    │
                       └─────────────┘

     Any state ──user_cancel()──► cancelled
```

### Event Schema (Canonical)

```json
{
  "event_id": "uuid",
  "event_type": "run.state_changed",
  "correlation_id": "uuid",
  "timestamp": "2026-03-26T12:00:00Z",
  "project_id": "uuid",
  "user_id": "uuid",
  "run_id": "uuid",
  "run_type": "mission | crew | workflow | voice | monitor | report",
  "data": {
    "from_state": "running",
    "to_state": "completed",
    "reason": null,
    "failure_category": null,
    "step_name": "expert_task:web_researcher",
    "metadata": {}
  }
}
```

### Audit Schema (Enhanced)

Current AuditLog stays. Add to every write operation:

```
correlation_id: UUID (traces to the request/task that caused this)
actor_type: Enum (user, system, celery_worker, action_executor)
```

### Evidence/Provenance Model

```
Source (existing)
  └──► Signal (new — Phase 2)
         └──► Observation (new — Phase 2)
                └──► Evidence (new — Phase 2)
                       ├──► Insight (new — Phase 2)
                       └──► Recommendation (new — Phase 2)
                              └──► ActionRequest (new — Phase 3)
                                     └──► ActionExecution (new — Phase 3)
                                            └──► ActionOutcome (new — Phase 3)
                                                   └──► Signal (feedback loop)
```

Every link in this chain is a foreign key. Users can click from a recommendation all the way back to the original source URL.

### Migration Strategy

- Phase 1: Additive columns only (no breaking changes to existing tables)
- Phase 2: New tables + FK links from existing models. Finding gets `observation_id` FK.
- Phase 3: New tables + FK links from Phase 2 models.
- Each phase is one Alembic migration. Rollback = `alembic downgrade -1`.

---

## 7. API AND WORKER DESIGN

### Background Job Contracts

| Queue | Tasks | Retry | Timeout | Idempotent |
|-------|-------|-------|---------|------------|
| `research` | `execute_crew_run`, `plan_and_start_mission` | 2x | 3600s | Yes (idempotency_key) |
| `voice` | `execute_call`, `process_completed`, `execute_batch` | 1x | 600s | Yes |
| `monitors` | `check_all_monitors`, `check_single_monitor` | 1x | 300s | Yes |
| `reports` | `generate_report`, `regenerate_section` | 1x | 600s | Yes |
| `workflows` | `execute_workflow_run` | 1x | 1800s | Yes |
| `signals` (Phase 2) | `process_signal`, `generate_insights` | 2x | 300s | Yes (signal_id dedup) |
| `actions` (Phase 3) | `execute_action`, `evaluate_policy` | 1x | 300s | Yes (action_request_id) |
| `dead_letter` | Failed tasks after max retries | N/A | N/A | N/A |

### Retry Semantics

```python
# All tasks follow this pattern:
@celery_app.task(
    bind=True,
    max_retries=MAX_RETRIES_FOR_QUEUE,
    acks_late=True,
    reject_on_worker_lost=True,
)
def task_name(self, run_id: str, idempotency_key: str):
    # 1. Check idempotency
    if already_completed(idempotency_key):
        return {"status": "skipped", "reason": "already_completed"}

    # 2. Execute with error categorization
    try:
        result = do_work(run_id)
    except TransientError as e:
        raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))
    except PermanentError as e:
        record_failure(run_id, category="validation", message=str(e))
        raise  # Goes to dead letter after max_retries

    # 3. Record success
    return result
```

### WebSocket Events (Complete List)

| Event Type | Payload | When |
|------------|---------|------|
| `run.state_changed` | `{run_id, run_type, from_state, to_state, reason}` | Any run status change |
| `run.step_completed` | `{run_id, step_name, step_type, duration_ms, tokens_used}` | CrewRunner step or workflow node completes |
| `agent.thinking` | `{expert_name, content}` | Agent begins reasoning |
| `agent.tool_call` | `{expert_name, tool_name, query}` | Agent calls a tool |
| `agent.found_data` | `{expert_name, finding_title, confidence}` | Agent produces finding |
| `finding.created` | `{finding_id, title, source_type, confidence}` | New finding persisted |
| `signal.created` | `{signal_id, signal_type, entity_name}` | Phase 2: new signal |
| `recommendation.created` | `{rec_id, title, priority, confidence}` | Phase 2: new recommendation |
| `action.pending_approval` | `{action_id, title, type, priority}` | Phase 3: action needs approval |
| `action.executed` | `{action_id, outcome_type}` | Phase 3: action completed |
| `monitor.alert` | `{monitor_id, alert_id, severity, title}` | Monitor fires alert |
| `system.health_changed` | `{service, old_state, new_state}` | Circuit breaker state change |

---

## 8. FRONTEND / UX PLAN

### Real-Time vs Polling Decision

| Page | Current | Phase 1 Target | Reason |
|------|---------|----------------|--------|
| Mission Live | Polling 2s | WebSocket | Core execution view — must be real-time |
| Workflow Run | Polling 5s | WebSocket | Node status updates need real-time |
| Dashboard | Polling 5s | WebSocket | Command center — real-time activity feed |
| Voice Calls | Polling | WebSocket | Call status changes rapidly |
| Signal Feed | N/A (Phase 2) | WebSocket | Signals arrive continuously |
| Recommendations | N/A (Phase 2) | REST + WS notification | List is REST, new items push via WS |
| Approval Inbox | N/A (Phase 3) | REST + WS notification | New approvals push via WS badge count |
| Entity Detail | N/A | REST (no real-time needed) | Static page with manual refresh |
| Reports | REST | REST (no change) | Reports don't change in real-time |
| Settings/Health | Polling 30s | Polling 30s (no change) | Low-frequency data |

### Key Screens by Phase

**Phase 1 (enhance existing):**
- Mission live view: replace polling with WS, add run trace timeline
- Workflow run view: replace polling with WS
- Dashboard: replace polling with WS
- Voice extraction detail: build from scratch
- Settings: add queue depths and worker count

**Phase 2 (new screens):**
- Entity detail page (history, aliases, relationships, insights, recommendations)
- Signal feed (real-time, filterable)
- Recommendation inbox (priority-sorted, accept/reject)
- Enhanced entity list (observation count, staleness indicator)

**Phase 3 (new screens):**
- Approval inbox (pending actions with evidence chain)
- Action detail (what/why/evidence/approve/reject)
- Action history (completed/failed/rejected)
- Operator console (system health + operational queues)

---

## 9. RELIABILITY AND EVAL FRAMEWORK

### Test Strategy

**Backend Unit Tests (Phase 1):**
- State machine: all valid transitions, all invalid transitions, transition history
- Policy engine: each default policy, edge cases
- Connector wrappers: mock external APIs, verify retry behavior
- Scoring logic: confidence calculation, freshness computation
- Schema parsing: Pydantic schema validation for all models

**Backend Integration Tests (Phase 1):**
- Mission golden path: create -> start -> crew assembly -> parallel execution -> findings -> complete
- Workflow golden path: create -> activate -> trigger -> node execution -> complete
- Monitor golden path: create -> check -> change detected -> alert -> notification
- Voice golden path: create session -> plan calls -> simulate call -> extract data

**E2E Tests (Phase 1):**
- Full mission flow via API (no browser)
- Full workflow flow via API
- WebSocket event delivery test

**Frontend Tests (Phase 1):**
- useWebSocket hook: connect, reconnect, parse events
- API client: auth header injection, error handling
- LiveActivityFeed: renders events, auto-scrolls

**Golden Path Evals (Phase 2+):**
- "Run a market research mission" -> produces findings with confidence > 0.5
- "Generate insights from 10+ observations" -> insights have evidence links
- "Generate recommendation" -> recommendation has rationale and priority

**Adversarial Evals:**
- Empty mission objective -> graceful failure with clear error
- All connectors fail -> run enters partially_failed, not stuck
- Gemini returns garbage -> validation catches it, task fails cleanly
- Concurrent identical dispatches -> idempotency prevents duplicate runs

---

## 10. READINESS RUBRIC

### Phase 1 -> Phase 2 Gate

| # | Criterion | Status |
|---|-----------|--------|
| 1 | All run types use formal state machine with transition tracking | [x] |
| 2 | Failed runs have categorized failure reason and inspectable step history | [x] |
| 3 | Celery tasks are idempotent with dead-letter queue configured | [x] |
| 4 | Mission, workflow, dashboard, voice pages use WebSocket (not polling) | [x] |
| 5 | Structured logging with correlation IDs on every request/task | [x] |
| 6 | RunStep trace model exists and is populated | [x] |
| 7 | Mission /run endpoint dispatches to Celery | [x] |
| 8 | Call post-processing uses Gemini for extraction | [x] |
| 9 | Python executor handles all methods without NotImplementedError | [x] |
| 10 | Voice extraction detail page exists | [x] |
| 11 | Monitor edge cases handled (unreachable, timeout, dedup) | [x] |
| 12 | 4+ integration tests passing in CI | [x] |
| 13 | >95% of valid test runs complete without manual intervention | [x] |
| 14 | No user-visible stubbed features on core paths | [x] |

**Gate rule:** All 14 criteria checked. ✓ PHASE 1 COMPLETE — ready for Phase 2.

### Phase 2 -> Phase 3 Gate

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Signal, Observation, Evidence, Insight, Recommendation models exist with migrations | [x] |
| 2 | All major run types emit Signals (missions, monitors, voice, workflows) | [x] |
| 3 | SignalProcessor extracts Observations from Signals | [x] |
| 4 | InsightGenerator synthesizes Observations into Insights with evidence links | [x] |
| 5 | RecommendationGenerator creates recommendations from Insights | [x] |
| 6 | Entity detail page shows observations, insights, recommendations | [x] |
| 7 | Signal feed page exists and updates in real-time | [x] |
| 8 | Recommendation inbox exists with accept/reject | [x] |
| 9 | EntityAlias model supports source-specific identifiers | [x] |
| 10 | Freshness indicators visible on insights and recommendations | [x] |
| 11 | Finding -> Observation migration adapter works | [x] |
| 12 | Evidence chain is navigable in UI (recommendation -> insight -> observation -> source) | [x] |

**Gate rule:** All 12 criteria checked. ✓ PHASE 2 COMPLETE — ready for Phase 3.

### Phase 3 Done

| # | Criterion | Status |
|---|-----------|--------|
| 1 | ActionRequest, ActionPolicy, ActionExecution, ActionOutcome models exist | [x] |
| 2 | PolicyEngine evaluates rules and determines approval requirement | [x] |
| 3 | Default policies seeded for all action types | [x] |
| 4 | At least 4 action types auto-execute per policy | [x] |
| 5 | Approval inbox shows pending actions with evidence chain | [x] |
| 6 | Approve/reject flow works end-to-end | [x] |
| 7 | ActionOutcome creates feedback Signal | [x] |
| 8 | Operator console shows pending approvals, failures, queue health | [x] |
| 9 | Action audit trail is complete and inspectable | [x] |
| 10 | Acceptance rate and success rate metrics tracked | [x] |

---

## 11. FINAL RECOMMENDATIONS

### Smallest Credible v1 (Phase 1 Only)

If you can only ship one thing, ship Epic 1.1 (state machine) + Epic 1.2 (durable orchestration) + Epic 1.5 (close stubs). This gives you:
- Reliable run lifecycle
- No mystery stuck states
- No exposed broken paths

Everything else in Phase 1 is important but these three make the system trustworthy.

### Highest-Risk Areas

1. **Signal -> Observation extraction (Phase 2)** — Depends on Gemini producing consistent structured output. Need robust validation and fallback.
2. **Recommendation quality (Phase 2)** — Bad recommendations erode trust faster than no recommendations. Ship with high confidence threshold initially.
3. **Auto-execution safety (Phase 3)** — A runaway auto-approve policy is dangerous. Default to require_approval and let users opt into auto.
4. **WebSocket reliability (Phase 1)** — Browser reconnection edge cases. Test on slow connections and after sleep/wake.

### What to Postpone

- Multi-team workspaces
- CRM ontology (lead/account/opportunity)
- External enterprise integrations (HubSpot, Salesforce, Calendly)
- Agent marketplace
- Public API platform
- Custom agent creation UI (current custom expert creation is sufficient)
- Advanced RBAC beyond user/project scoping

### Preserving CRM Optionality

Phase 3's action architecture is designed so that `action_type` can later include:
- `sync_to_crm` — write to HubSpot/Salesforce
- `create_ticket` — create in Jira/Linear
- `schedule_meeting` — book via Cal.com/Calendly
- `send_email` — via outreach platform

These are just new action handlers registered with the ActionDispatcher. The policy engine, approval flow, and outcome tracking work unchanged. No rewrite needed.

Similarly, Entity can later gain:
- `external_ids: JSONB` — mapping to CRM record IDs
- `sync_status: Enum` — tracking CRM sync state

These are additive columns, not breaking changes.

---

## 12. KEY QUESTIONS ANSWERED

**What should the core domain objects be if this is vertical-first and not CRM-first?**

Entity, Signal, Observation, Evidence, Insight, Recommendation, ActionRequest, ActionOutcome. These describe what the system knows, how it knows it, and what it proposes to do — without assuming any specific vertical ontology.

**What does "system of intelligence" mean in implementation terms?**

It means: every run output becomes a Signal. Signals become Observations. Observations accumulate into Insights with evidence chains. Insights generate Recommendations. All of this is queryable, navigable, and visible in the UI. The system has memory across runs.

**What makes an agentic product trustworthy enough for real usage?**

Three things: (1) Every run has a visible lifecycle — no mystery states. (2) Every output has provenance — users can see where data came from and how fresh it is. (3) Every consequential action has a gate — policy, approval, or at minimum an audit trail.

**How should evidence, provenance, freshness, and confidence be represented?**

- Evidence: FK chain from Recommendation -> Evidence -> Observation -> Signal -> Source
- Provenance: `source_type`, `source_url`, `source_name` on every Observation
- Freshness: `freshness_at` timestamp + `staleness_threshold_hours` on Insights
- Confidence: Float 0-1 on Signal, Observation, Insight, Recommendation — computed differently at each level

**What should be event-driven vs synchronous?**

- Event-driven: Signal processing, insight generation, recommendation generation, action dispatch, monitor checks, real-time UI updates
- Synchronous: CRUD operations, authentication, health checks, report downloads, entity merges (user-initiated)

**How should workflows, monitors, missions, voice, and reports converge?**

All of them emit Signals. Signals feed the same Observation -> Evidence -> Insight pipeline. The intelligence layer is the convergence point. Each product surface is a different way of producing or consuming shared domain objects.

**What must exist before action-taking is safe?**

Policy engine with default-to-approval. Audit trail. Typed action requests with evidence links. Approval UI with evidence view. Outcome tracking. These are Phase 3 prerequisites, and Phase 2's intelligence layer is a prerequisite for Phase 3.

**How should the architecture remain adaptable for later CRM integration?**

Entity model + action architecture are the extension points. Entity gains `external_ids` for CRM mapping. ActionDispatcher gains new handlers for CRM sync. Policy engine gains new conditions for CRM-specific rules. All additive, no rewrites.

---

*End of Blueprint. This document is the source of truth for Agentary Phases 1-3. Update it as implementation proceeds.*
