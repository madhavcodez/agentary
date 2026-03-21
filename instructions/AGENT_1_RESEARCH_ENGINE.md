# AGENT 1 — Research Engine & Expert Agent Crews

## YOUR MISSION

You are a Claude Code agent running with `claude --dangerously-skip-permissions`. Build the **core research engine and mixture-of-experts crew system** — the brain of Agentary. This is the most important module.

**Start:** `/plan Read this entire file, explore the repo (especially what Agent 0 set up), then build everything in order.`

---

## WHAT YOU'RE BUILDING

When a user creates a research mission, the system: (1) Analyzes it and picks Expert Agents, (2) Assembles a Crew, (3) Experts research in parallel using tools (web search, APIs, voice calls, data analysis), (4) Users WATCH experts work in real-time (thinking_log on each task), (5) Findings have source attribution + confidence scores, (6) Synthesizer combines, identifies gaps, triggers follow-up, (7) ReportWriter outputs final results.

### Example: "Research housing market in Austin 78704"
```
🔍 WebResearcher → searches Zillow, Redfin, Realtor.com
📊 DataAnalyst → pulls county records, analyzes comps/trends  
📞 VoiceCaller → calls local real estate offices
🏠 PropertyResearcher → deep-dives MLS, permits, tax records
🧠 Synthesizer → combines findings, identifies gaps
📝 ReportWriter → generates final report
```

---

## MODELS TO CREATE (backend/app/models/)

### expert_agent.py
Fields: id (UUID PK), user_id (FK users, nullable=null means system agent), name (str 255), slug (str 100 unique), description (Text), avatar_emoji (str 10), category (str: research|analysis|extraction|synthesis|output), capabilities (ARRAY String), tools (ARRAY String), system_prompt (Text NOT NULL), model (str default "gemini-2.5-flash"), temperature (Float 0.3), max_tokens (Int 8192), is_system (Bool), is_active (Bool), created_at, updated_at.

### mission.py
Fields: id (UUID PK), project_id (FK projects), user_id (FK users), title (str 500), description (Text), objective (Text), scope (JSONB — geography, time_range, depth, budget_limit), status (str: pending|planning|in_progress|completed|failed|cancelled), required_experts (ARRAY String — slugs or null for auto), max_experts (Int 5), priority (str), schedule_cron (str nullable), is_recurring (Bool), summary (Text), confidence_score (Float 0-1), findings_count (Int), duration_seconds (Float), created_at, updated_at, started_at, completed_at. Relationships: project, crew_runs, findings, research_results.

### agent_crew.py
Fields: id (UUID PK), mission_id (FK missions), name (str), expert_agent_ids (ARRAY UUID), lead_agent_id (FK expert_agents), collaboration_mode (str: parallel|sequential|hierarchical default parallel), max_iterations (Int 3), time_limit_seconds (Int 3600), status (str: assembled|running|completed|failed), created_at. Relationships: mission, runs.

### crew_run.py
Fields: id (UUID PK), crew_id (FK agent_crews), mission_id (FK missions), status (str: queued|running|completed|failed|cancelled), trigger_type (str: manual|scheduled|monitor_triggered), iteration (Int), started_at, completed_at, duration_seconds (Float), summary (Text), metrics (JSONB: findings_count, sources_queried, voice_calls_made, tokens_used, cost_usd), error (JSONB), created_at. Relationships: crew, mission, tasks.

### crew_task.py
Fields: id (UUID PK), run_id (FK crew_runs), expert_agent_id (FK expert_agents), task_type (str: web_search|api_query|voice_call|data_analysis|synthesis|report_writing|entity_extraction|comparison|trend_analysis|fact_verification), description (Text), input_data (JSONB), status (str: pending|running|completed|failed|skipped), **thinking_log (JSONB)** — array of {timestamp, thought, action, tool, result_preview} — THIS IS WHAT THE LIVE DASHBOARD SHOWS, output_data (JSONB), findings_produced (Int), started_at, completed_at, duration_seconds (Float), tokens_used (Int), cost_usd (Float), retry_count (Int), error_message (Text), created_at. Relationships: run, expert_agent.

### finding.py
Fields: id (UUID PK), mission_id (FK missions), crew_task_id (FK crew_tasks nullable), expert_agent_id (FK expert_agents nullable), category (str: data_point|insight|trend|risk|opportunity|fact|quote|statistic|comparison), title (str 500), content (Text NOT NULL), structured_data (JSONB), source_type (str: web|api|voice_call|calculation|inference), source_url (Text), source_name (str), source_raw (Text), confidence (Float 0-1 default 0.5), verified (Bool default false), verification_sources (JSONB), entity_id (FK entities nullable), tags (ARRAY String), created_at. Relationship: mission.

### research_result.py
Fields: id (UUID PK), mission_id (FK missions), crew_run_id (FK crew_runs nullable), title (str 500), summary (Text), sections (JSONB — array of {title, content, finding_ids, chart_configs}), structured_data (JSONB), raw_data (JSONB), sources_used (Int), findings_count (Int), confidence (Float), methodology (Text), created_at. Relationship: mission.

---

## 8 BUILT-IN EXPERT AGENTS

Create `backend/app/services/crews/expert_registry.py` with a BUILTIN_EXPERTS list. Each expert needs a **detailed system prompt** (300+ words) defining personality, methodology, output format, and rules.

1. **Web Researcher** (🔍, category=research) — tools: gemini_search, exa_search, web_scraper. Searches web, extracts info, cites sources, rates confidence.
2. **Data Analyst** (📊, category=analysis) — tools: python_executor, chart_generator. Analyzes data, calculates statistics, identifies trends, creates charts.
3. **Voice Caller** (📞, category=extraction) — tools: voice_caller, transcript_analyzer. Calls businesses/people to extract specific info. Polite, structured questions.
4. **Synthesizer** (🧠, category=synthesis) — tools: none. Combines findings from all experts, resolves contradictions, identifies gaps, recommends follow-ups.
5. **Report Writer** (📝, category=output) — tools: chart_generator, pdf_generator. Generates polished reports with sections, charts, citations.
6. **Market Analyst** (📈, category=analysis) — tools: gemini_search, exa_search, web_scraper, python_executor. Market research, competitive analysis, pricing, SWOT.
7. **Property Researcher** (🏠, category=research) — tools: zillow_api, mls_connector, county_records, web_scraper, gemini_search. Real estate specialist.
8. **Local Scout** (📍, category=research) — tools: google_places, yelp_connector, web_scraper, voice_caller. Local business research, reviews, area intel.

Implement: `seed_builtin_experts(db)`, `select_experts_for_mission(mission, db)` (uses Gemini to pick crew), `create_custom_expert(user_id, data, db)`.

---

## CORE SERVICES

### crew_runner.py — THE EXECUTION ENGINE (most important file)

```python
class CrewRunner:
    async def execute_run(self, run_id: UUID):
        """
        1. Load run, crew, mission, experts
        2. Emit CREW_RUN_STARTED event
        3. Separate researchers from synthesizer/report_writer
        4. PARALLEL PHASE: All researchers execute simultaneously via asyncio.gather
        5. Each expert runs agentic loop:
           while not done:
             response = await gemini.generate(messages, tools=expert_tools)
             if response.has_tool_call:
               result = await tool_registry.execute(tool_name, tool_args)
               emit EXPERT_THINKING event (user sees this in real-time!)
               messages.append(tool_result)
             else:
               findings = parse_findings(response)
               done = True
        6. SYNTHESIS PHASE: Synthesizer receives all findings, combines, finds gaps
        7. If gaps AND iterations remaining → targeted follow-up research
        8. REPORT PHASE: ReportWriter generates structured output
        9. Emit CREW_RUN_COMPLETED
        """
```

At EVERY step, emit events so the live dashboard shows expert activity:
- `EXPERT_THINKING`: {task_id, expert_name, expert_emoji, thought, action, tool, result_preview}
- `CREW_TASK_STARTED/COMPLETED`: {task_id, expert_name, task_type}
- `RESEARCH_FINDING_ADDED`: {finding_title, confidence, source}

### task_planner.py
Uses Gemini to analyze a mission and create a task plan: which experts do what, in what order, what specific questions to research.

### tool_registry.py
Registry of tools experts can use. Each tool has: name, description, parameters (JSON schema for Gemini function calling), execute() method. Implement at minimum: gemini_search (existing), exa_search (existing), web_scraper (httpx + BeautifulSoup), python_executor (subprocess with timeout), voice_caller (stub for Agent 2), chart_generator (returns Chart.js JSON).

### crew_service.py
`assemble_crew(mission)` — select experts, create AgentCrew. `start_crew_run(crew_id, trigger)` — create CrewRun, enqueue Celery. `get_crew_status(crew_id)` — real-time status.

---

## API ROUTES

**`/api/missions`**: POST / (create), GET /{id} (detail), POST /{id}/start (assemble crew + start), POST /{id}/stop, GET /{id}/findings (with filters: category, confidence_min, expert, source_type), GET /{id}/findings/structured (table view), GET /{id}/status (real-time crew status), POST /{id}/rerun.

**`/api/crews`**: GET /{crew_id}/runs, GET /{crew_id}/runs/{run_id} (with task timeline + thinking_logs), GET /{crew_id}/runs/{run_id}/live (polling for live status).

**`/api/experts`**: GET / (list all), GET /{slug}, POST / (create custom), PUT /{id} (update custom).

---

## CELERY TASKS

```python
@celery_app.task(name="crew.execute_run", queue="crew_runs", bind=True,
                 max_retries=2, soft_time_limit=3600, time_limit=3900)
def execute_crew_run(self, run_id: str): ...

@celery_app.task(name="mission.plan_and_start", queue="crew_runs")  
def plan_and_start_mission(mission_id: str): ...
```

---

## FRONTEND PAGES

### Mission Detail (`/projects/[id]/missions/[missionId]`) — THE MAIN PAGE

1. **Mission Header** — title, status, objective
2. **Expert Crew Panel** — row of expert avatars with live status (✅ Done, ⏳ Working, 🟡 Waiting, ⬜ Pending) and findings count
3. **Live Activity Feed** — scrolling log of expert thoughts/actions in real-time:
   ```
   🔍 Searching "Austin 78704 median home price 2024"...
   📊 Calculating price trends from 47 comparable sales...
   📞 Calling Keller Williams at (512) 555-1234...
   🧠 Gap identified: No permit data. Requesting follow-up...
   ```
4. **Findings Panel** — cards with title, content preview, confidence badge, source link, expert avatar. Filter/sort controls.
5. **Structured Data Tab** — interactive table of all data points
6. **Actions** — Re-run, Export, Generate Report, Add Expert

### Quick Mission Input (on project page)
```
🔍 What do you want to research? [________________________________] [Start]
```
Creates mission, auto-selects experts, starts immediately.

---

## TESTING

- All 7 model creation tests
- Expert registry: all 8 built-in experts created
- Task planner: produces valid plan for sample missions
- Crew assembly: correct experts for "real estate research" vs "competitive analysis"
- Finding creation with source attribution
- API CRUD tests for missions, crews, experts
- **E2E golden path**: create mission → assemble crew → mock execute → verify findings exist

---

## SUCCESS CRITERIA (Agent 7 Checks)

- [ ] All 7 models created with Alembic migrations
- [ ] 8 built-in expert agents with detailed system prompts (300+ words each)
- [ ] CrewRunner implements parallel execution with agentic tool-calling loop
- [ ] Events emitted at every step (EXPERT_THINKING visible in thinking_log)
- [ ] TaskPlanner creates research plans via Gemini
- [ ] Tool registry with 6+ tools (gemini_search, exa_search, web_scraper, python_executor, voice_caller stub, chart_generator)
- [ ] Findings stored with source, confidence, structured_data
- [ ] All API routes functional
- [ ] Frontend: mission detail page with live activity feed + findings panel
- [ ] Celery tasks for background execution
- [ ] Tests passing
- [ ] docs/PHASE_1_PROGRESS.md updated
