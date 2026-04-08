# AGENT 0 — Foundation & Domain Restructure

## YOUR MISSION
You are an autonomous coding agent. Fully complete Phase 0 — rename SecretAIRY → Agentary, replace ALL job-search domain language with research/intelligence domain language, create every new database model, set up Celery, events, telemetry, and scaffold the entire new directory structure.

**Run with:** `agent-cli --dangerously-skip-permissions -p "Read AGENT_0_FOUNDATION.md in the current directory, then execute every step. Use /plan first to create your approach, then build everything. Do not stop until all success criteria are met. Loop back and verify." --max-turns 200`  
Replace `agent-cli` with your installed coding CLI command.

---

## WHAT AGENTARY IS (READ THIS CAREFULLY)

**Agentary is an autonomous research & intelligence platform.** NOT a CRM. NOT a sales tool. NOT a lead pipeline.

Users create **Projects** (e.g. "Austin Real Estate Market Analysis"), define research **Missions** (e.g. "Find all new permits in 78701"), and deploy crews of specialized **Expert Agents** (MarketAnalyst, DataExtractor, VoiceCaller, etc.) that collaborate visibly. Agents use web research, phone calls, data APIs, and domain expertise to gather **Findings**, which become structured **DataSets** and narrative **Reports**. Users see everything on a **live dashboard** with a birds-eye workflow view.

### Example Use Cases
- Real estate: Pull MLS data, county records, permits, call offices, analyze comps, generate report
- Competitive intel: Track competitor pricing, features, reviews, job postings, generate weekly brief
- Due diligence: Deep research on company before deal — financials, sentiment, regulatory, references
- Local business data: Call 50 gas stations for current prices, compile into structured dataset
- Market research: Analyze demand signals, existing players, gaps, generate opportunity report

### Existing Tech Stack
Backend: FastAPI, SQLAlchemy, Pydantic, PostgreSQL, Redis, Qdrant, Alembic | Frontend: Next.js 14, React 18, Tailwind | Voice: Pipecat + Gemini Live + Twilio | LLM: Gemini 2.5 Flash | Search: Exa API | Email: Resend | Infra: Docker Compose, Nginx

---

## THE COMPLETE DOMAIN RENAME MAP

```
OLD (SecretAIRY)              →  NEW (Agentary)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Opportunity (job listing)     →  REMOVED (no equivalent)
Match / match_engine          →  REMOVED (replaced by expert scoring)
Dossier / dossier_gen         →  Report / report_gen
Profile (resume)              →  KnowledgeBase (user domain knowledge)
CallCampaign                  →  VoiceExtraction
Autopilot / autopilot.py      →  MissionRunner / mission_runner.py
Scout / scout.py              →  LiveFeed / live_feed.py
Pipeline / pipeline_engine    →  REMOVED (no sales pipeline)
outreach_gen                  →  REMOVED (no cold outreach)
SecretAIRY / secretairy       →  Agentary / agentary everywhere
```

### NEW entities to create from scratch:
Project, Mission, MissionRun, MissionTask, ExpertAgent, AgentCrew, AgentActivity, Finding, DataSet, DataRow, Report, VoiceExtraction, CallRecord, Workflow, WorkflowNode (via JSONB), Monitor, Alert, KnowledgeBase, Source, AuditLog

---

## EXECUTION STEPS

### STEP 1: Explore and Inventory (15 min)
```bash
# Run these first
find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) | head -200
tree backend/ -I __pycache__ -L 4
tree frontend/ -I node_modules -L 4
grep -rn "SecretAIRY\|secretairy\|Opportunity\|Dossier\|match_engine\|autopilot\|pipeline_engine" --include="*.py" -l
grep -rn "SecretAIRY\|secretairy\|Opportunity\|Dossier" --include="*.ts" --include="*.tsx" -l
```
Create `docs/RENAME_MAP.md` documenting every file that needs changes.

### STEP 2: Create New Directory Structure
```
backend/app/
  api/routes/      → projects.py, missions.py, agents.py, research.py, voice.py,
                     workflows.py, monitors.py, reports.py, datasets.py, findings.py,
                     sources.py, live_feed.py, auth.py, knowledge_base.py
  core/            → config.py, database.py, auth.py, permissions.py, events.py,
                     telemetry.py, feature_flags.py
  models/          → ALL new models (see below)
  schemas/         → ALL new Pydantic schemas
  services/        → projects/, missions/, agents/, research/, voice/, workflows/,
                     monitors/, reports/, datasets/, sources/, analytics/, policies/
  tasks/           → celery_app.py, mission_runs.py, research_tasks.py, voice_tasks.py,
                     monitor_tasks.py, report_tasks.py
  providers/       → gemini/, exa/, twilio/, resend/
  tests/
frontend/app/      → projects/, missions/, dashboard/, workflows/, reports/, voice/,
                     monitors/, settings/, login/
frontend/components/ → projects/, missions/, agents/, research/, voice/, workflows/,
                       dashboard/, reports/, monitors/, common/
frontend/lib/      → api/, auth/, hooks/, types/, websocket/
```
Create ALL directories. Create `__init__.py` in every Python directory.

### STEP 3: Create ALL Database Models

Create these files with COMPLETE SQLAlchemy model definitions. Every column, every relationship, every index.

**`models/project.py`** — Project container
- id (UUID PK), user_id (FK users), name, description, status (active/archived/completed), project_type (market_research/competitive_intel/due_diligence/data_extraction/real_estate/local_business/custom), domain_context (Text), knowledge_base_id (FK), default_workflow_id (FK), total_missions, total_findings, total_calls_made, total_reports_generated, created_at, updated_at
- Relationships: missions, findings, reports, monitors, datasets, voice_extractions

**`models/mission.py`** — Research mission within a project
- id, project_id (FK), user_id (FK), name, description, objective (Text — what to find out), status (draft/queued/running/paused/completed/failed), mission_type (research/voice_extraction/monitoring/data_collection/competitive_analysis/custom), instructions (Text — NL instructions), parameters (JSONB — flexible config), workflow_id (FK), crew_config (JSONB), schedule_cron, timezone, summary, findings_count, confidence_score, started_at, completed_at, created_at, updated_at
- Relationships: project, crew, findings, runs

**`models/expert_agent.py`** — Specialized AI agent type (the "experts")
- id, slug (unique), name, description, specialty (web_researcher/data_extractor/voice_caller/market_analyst/financial_analyst/real_estate_expert/competitive_intel/due_diligence/synthesizer/local_business_intel), system_prompt (Text), tools (JSONB array), model_config (JSONB), icon, color (hex for UI), is_system (bool), is_active, created_at

**`models/agent_crew.py`** — Team of experts for a mission + AgentActivity for live feed
- AgentCrew: id, mission_id (FK), agents (JSONB — [{agent_id, role, config_overrides}]), coordination_strategy (parallel/sequential/hierarchical), created_at
- AgentActivity: id, mission_id (FK), run_id (FK), expert_agent_id (FK), activity_type (thinking/searching/scraping/calling/analyzing/writing/found_data/found_insight/error/delegating/synthesizing), content (Text), metadata (JSONB), confidence (Float), created_at

**`models/mission_run.py`** — Execution of a mission + individual tasks
- MissionRun: id, mission_id (FK), status (queued/running/completed/failed/cancelled), trigger_type (manual/scheduled/monitor_triggered), config_snapshot (JSONB), started_at, completed_at, summary, metrics (JSONB: sources_queried, findings_count, calls_made, data_points_extracted, duration_seconds, tokens_used, cost_estimate), error (JSONB), created_at
- MissionTask: id, run_id (FK), expert_agent_id (FK), task_type (discover/research/extract/call/analyze/synthesize/report/monitor_check), status, input_data (JSONB), result_data (JSONB), error_message, started_at, completed_at, duration_seconds, retry_count, created_at

**`models/finding.py`** — Single discovered fact/data point
- id, project_id (FK), mission_id (FK), expert_agent_id (FK), finding_type (fact/data_point/insight/quote/statistic/contact_info/price/availability/sentiment/trend/anomaly/opportunity/risk), title, content (Text), structured_data (JSONB), source_type (web/voice_call/api/public_record/user_provided/inferred), source_url, source_name, source_metadata (JSONB), confidence (Float 0-1), verified (bool), verified_by, contradicts (UUID FK to another finding), tags (JSONB), entity_refs (JSONB — [{type, name, id}]), created_at

**`models/dataset.py`** — Structured tabular data + DataRow
- DataSet: id, project_id (FK), mission_id (FK), name, description, schema_definition (JSONB — {columns: [{name, type}]}), row_count, data (JSONB for small), file_path (for large), created_at, updated_at
- DataRow: id, dataset_id (FK), data (JSONB), source_finding_id (FK), created_at

**`models/report.py`** — Generated narrative report
- id, project_id (FK), mission_id (FK), title, report_type (market_analysis/competitive_brief/due_diligence/data_summary/voice_extraction_summary/custom), status (generating/completed/failed), content_markdown, content_html, file_path, sections (JSONB), executive_summary, key_findings (JSONB), confidence_score, sources_cited, created_at, updated_at

**`models/voice_extraction.py`** — Voice call campaign + CallRecord
- VoiceExtraction: id, project_id (FK), mission_id (FK), name, description, status (draft/active/paused/completed), objective (Text), persona (JSONB: {name, role, tone, company_context, opening_script}), extraction_schema (JSONB: {fields: [{name, type, question}]}), call_script_template, objection_handlers (JSONB), max_call_duration_seconds, business_hours_only, targets (JSONB), total_targets, calls_completed, calls_successful, data_points_extracted, created_at, updated_at
- CallRecord: id, voice_extraction_id (FK), mission_id (FK), project_id (FK), phone_number, target_name, target_context (JSONB), provider_call_id, direction, status (pending/ringing/connected/completed/failed/no_answer/voicemail), recording_url, transcript, duration_seconds, extracted_data (JSONB), extraction_confidence, extraction_notes, sentiment, call_quality_score, started_at, ended_at, created_at

**`models/workflow.py`** — Reusable research workflow (node graph)
- id, user_id (FK nullable — null=system template), name, description, category (real_estate/competitive_intel/due_diligence/market_research/data_extraction/custom), is_template, is_public, nodes (JSONB: [{id, type, label, config, position: {x,y}}]), edges (JSONB: [{id, source_node_id, target_node_id, condition}]), parameters (JSONB: [{name, type, default, description}]), version, created_at, updated_at
- Node types: source, research, voice_call, api_query, analyze, filter, transform, merge, report, alert, human_review, llm_process

**`models/monitor.py`** — Ongoing watch + Alert
- Monitor: id, project_id (FK), user_id (FK), name, description, status (active/paused/expired), monitor_type (price_watch/competitor_track/news_alert/listing_watch/regulatory_change/job_posting_signal/review_sentiment/custom), target (JSONB), check_schedule (cron), alert_rules (JSONB: [{condition, severity, channels}]), last_checked_at, last_alert_at, created_at, updated_at
- Alert: id, monitor_id (FK), project_id (FK), severity (low/medium/high/critical), title, content, data (JSONB), acknowledged (bool), acknowledged_at, created_at

**`models/knowledge_base.py`** — User domain knowledge (replaces Profile/resume)
- id, user_id (FK), name, description, domain (real_estate/finance/technology/healthcare/retail/custom), context_text (Text), entities (JSONB), terminology (JSONB), preferences (JSONB), documents (JSONB), qdrant_collection, created_at, updated_at

**`models/source.py`** — External data source adapter config
- id, user_id (FK nullable), name, source_type (web_search/web_scrape/api/public_records/mls/county_records/voice/rss/social_media/file_upload/database), adapter_slug, config (JSONB), credentials (JSONB ref), rate_limit (JSONB), is_active, is_system, created_at

**`models/audit_log.py`** — Universal audit trail
- id, user_id (FK), project_id (FK nullable), entity_type, entity_id, action (created/updated/deleted/executed/accessed), details (JSONB), ip_address, created_at

### STEP 4: Create ALL Pydantic Schemas
For EVERY model above, create request schemas (Create, Update) and response schemas. Put them in `schemas/` directory matching model files. Use Pydantic V2 style with `model_config = ConfigDict(from_attributes=True)`.

### STEP 5: Create Core Infrastructure

**`core/events.py`** — Event bus with Redis pub/sub for WebSocket broadcast. Define EventType enum with ALL events: project.*, mission.*, agent.thinking/searching/scraping/calling/analyzing/writing/found_data/found_insight/error, finding.*, call.*, monitor.*, report.*. Include EventBus class with subscribe/publish/broadcast methods.

**`core/feature_flags.py`** — Simple dict-based flags for all features, all defaulting True.

**`core/telemetry.py`** — Structured logging with structlog. Include `tracked_operation` async context manager that logs start/end/duration/errors for any operation.

**`core/permissions.py`** — Basic permission check stubs (will be expanded in Phase 6).

**`tasks/celery_app.py`** — Celery configured with Redis broker, queues for: missions, research, voice, monitors, reports, workflows, analytics. Include beat schedule stub.

### STEP 6: Create API Route Stubs
For every route file listed in STEP 2, create a FastAPI router with proper prefix, tags, and endpoint stubs that return proper schemas. Each endpoint should have:
- Proper path and method
- Dependency injection for auth (get_current_user) and DB session
- Request/response schemas
- A stub implementation that either works (for simple CRUD) or returns a TODO response

Key routes:
- `POST/GET /api/projects` — CRUD
- `POST/GET /api/projects/{id}/missions` — mission management
- `POST /api/missions/{id}/run` — trigger mission execution
- `GET /api/missions/{id}/runs/{run_id}` — run status
- `GET /api/expert-agents` — list available experts
- `GET /api/live-feed/{project_id}` — WebSocket for live dashboard
- `POST/GET /api/voice-extractions` — voice campaign management
- `POST/GET /api/workflows` — workflow CRUD
- `POST/GET /api/monitors` — monitor management
- `GET /api/reports` — report listing
- Plus all the detail/update/delete variants

### STEP 7: Remove Old Domain Code
1. Archive old files to `_archive/` (don't delete — other agents may reference patterns)
2. Remove old route registrations from main app
3. Register ALL new routes in main FastAPI app
4. Remove old frontend pages and components
5. Create ALL new frontend stub pages (just basic layout + "Coming soon" or empty state)

### STEP 8: Create Alembic Migration
Single migration that creates ALL new tables. If old tables exist, rename/archive them first. Test migration runs forward and backward.

### STEP 9: Seed Data
Create `scripts/seed.py` with:
- 10 default ExpertAgent records (web_researcher, data_extractor, voice_caller, market_analyst, financial_analyst, real_estate_expert, competitive_intel, due_diligence, synthesizer, local_business_intel) — each with proper system_prompt, tools list, icon, color
- 5 default Workflow templates (Real Estate Market Analysis, Competitive Intel Brief, Company Due Diligence, Local Business Data Collection, Market Gap Analysis) — each with proper nodes and edges
- Default Source records (gemini_search, exa_search, web_scraper, twilio_voice)

### STEP 10: Docker & Infra Updates
1. Rename Docker Compose services: secretairy_* → agentary_*
2. Add `celery_worker` and `celery_beat` services
3. Update Nginx
4. Update .env.example
5. Rewrite README.md

### STEP 11: Frontend Restructure
1. Update `layout.tsx` / root nav with new routes: Projects, Dashboard, Workflows, Voice, Monitors, Reports, Settings
2. Create stub pages for every route listed above
3. Update all TypeScript types in `lib/types/`
4. Update API client functions in `lib/api/`
5. Replace "SecretAIRY" with "Agentary" in ALL UI text

### STEP 12: Tests & Validation
1. All models importable and creatable
2. All API routes return proper responses
3. Migration runs clean
4. Frontend builds without errors
5. Docker Compose starts without errors
6. Zero old domain terms in critical runtime path

---

## SUCCESS CRITERIA
- [ ] Zero "SecretAIRY" references in runtime code
- [ ] ALL 20+ new model files created with complete definitions
- [ ] ALL Pydantic schemas created
- [ ] ALL API route stubs created and registered
- [ ] Alembic migration runs cleanly
- [ ] core/events.py, core/telemetry.py, core/feature_flags.py exist and work
- [ ] tasks/celery_app.py configured
- [ ] Seed script creates default ExpertAgents, Workflows, Sources
- [ ] Frontend restructured with new nav and stub pages
- [ ] Docker Compose starts with Celery worker + beat
- [ ] docs/PHASE_0_PROGRESS.md tracks completion
