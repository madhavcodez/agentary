# AGENT 3 — Workflow Engine

## YOUR MISSION

You are a coding agent. Build the **workflow engine** — users define custom research workflows via three interfaces: **templates** (quick start), **natural language** ("do X then Y then Z"), and a **visual node editor** (drag-and-drop for power users).

**Start:** `/plan Read this entire file, explore the repo, then build everything.`

---

## WHAT YOU'RE BUILDING

### Three Ways to Create Workflows

**Templates**: Pick "Real Estate Market Analysis" → pre-configured pipeline → customize params (location, price range)

**Natural Language**: "Every Monday, check gas prices at stations within 5 miles, call any without online prices, compile comparison, email me" → system generates workflow automatically via Gemini

**Visual Node Editor**: Drag nodes onto canvas, connect them: [Google Places] → [Filter] → [Web Scrape] → [Voice Call Gaps] → [Merge] → [Report]

---

## MODELS

### workflow.py
Fields: id (UUID PK), project_id (FK projects), user_id (FK users), name (str 255), description (Text), status (str: draft|active|paused|archived), trigger_type (str: manual|scheduled|event), trigger_config (JSONB: {cron, timezone} or {event_type, conditions}), created_from (str: template|natural_language|visual_editor|api), template_id (FK workflow_templates nullable), nodes (JSONB — full node definitions), edges (JSONB — connections [{source_node_id, target_node_id, source_port, target_port}]), variables (JSONB — user-defined variables nodes reference), last_run_at, total_runs (Int), avg_duration_seconds (Float), created_at, updated_at.

### workflow_run.py
Fields: id (UUID PK), workflow_id (FK workflows), user_id (FK users), status (str: queued|running|completed|failed|cancelled), trigger_type, started_at, completed_at, duration_seconds (Float), node_results (JSONB — {node_id: {status, output, duration, error}}), output_data (JSONB), findings_generated (Int), error (JSONB), created_at.

### workflow_template.py
Fields: id (UUID PK), user_id (FK users nullable), name (str 255), description (Text), category (str: real_estate|competitive_intel|local_business|due_diligence|price_monitoring|people_research|custom), tags (ARRAY String), nodes_template (JSONB), edges_template (JSONB), variables_schema (JSONB — [{name, type, label, required, default, description}]), is_system (Bool), is_public (Bool), install_count (Int), created_at, updated_at.

---

## NODE TYPES (implement ALL of these)

### Source/Trigger Nodes
- **manual_trigger** — start manually
- **schedule_trigger** — cron schedule. Config: {cron, timezone}
- **webhook_trigger** — external webhook. Config: {secret}

### Research Nodes
- **web_search** — config: {query_template, num_results, search_engine: gemini|exa}
- **api_query** — config: {source_type, endpoint, params_template}
- **web_scrape** — config: {url_template, selectors, extract_fields}
- **voice_call** — config: {target_source: "input"|"google_places", extraction_template_id, questions}
- **expert_research** — config: {expert_slug, task_description}

### Data Nodes
- **filter** — config: {conditions: [{field, op: eq|ne|gt|lt|contains|in, value}]}
- **transform** — config: {operations: [{type: rename|calculate|format, ...}]}
- **merge** — config: {strategy: concat|join|zip, key_field}
- **deduplicate** — config: {match_fields, strategy: exact|fuzzy}
- **sort** — config: {field, direction: asc|desc}
- **aggregate** — config: {group_by, aggregations: [{field, func: count|sum|avg|min|max}]}

### Analysis Nodes
- **ai_analyze** — config: {prompt_template, output_format: json|text}
- **compare** — config: {comparison_type: side_by_side|diff|ranking, metrics}
- **trend_detect** — config: {time_field, value_fields}

### Output Nodes
- **generate_report** — config: {report_type, sections}
- **generate_chart** — config: {chart_type: bar|line|pie|scatter, x_field, y_field}
- **export_data** — config: {format: csv|json|excel}
- **send_email** — config: {to_template, subject_template, body_template}
- **send_alert** — config: {channel: email|dashboard, condition, message_template}
- **save_findings** — config: {category, confidence_default}

### Control Flow
- **condition** — config: {expression, true_path, false_path}
- **loop** — config: {collection_source: "input", item_variable}
- **delay** — config: {seconds}
- **human_review** — config: {prompt, timeout_hours}

---

## SERVICES

### workflow_service.py
- `create_workflow(user_id, data)` — manual creation
- `create_from_template(user_id, template_id, variables)` — instantiate template, fill variables
- `create_from_natural_language(user_id, project_id, description: str)` — **THE MAGIC FEATURE**: use Gemini to parse NL into workflow
- `validate_workflow(workflow)` — no orphan nodes, no invalid cycles, required configs present
- `activate_workflow(workflow_id)` — set active, register Celery Beat if scheduled
- `trigger_run(workflow_id, trigger="manual")` — create WorkflowRun, enqueue

### workflow_executor.py — THE EXECUTION ENGINE
```python
async def execute_run(self, run_id):
    # 1. Load workflow (nodes + edges)
    # 2. Build execution DAG via topological sort
    # 3. Execute nodes in order, passing outputs → inputs via edges
    # 4. Handle branches (condition), loops, delays
    # 5. Emit events for each node start/complete (live dashboard)
    # 6. Collect final outputs

async def execute_node(self, node, input_data, context):
    # Route to handler based on node_type
    handlers = {"web_search": handle_web_search, "filter": handle_filter, ...}
```

Each node handler calls the appropriate service/connector from Agent 5's data sources.

### nl_workflow_builder.py — Natural Language to Workflow
```python
async def build_workflow(self, description: str, project_context: dict = None):
    # Prompt Gemini with:
    # 1. All available node types and their configs
    # 2. Example NL → workflow conversions
    # 3. The user's description
    # 4. Ask for structured JSON output: {nodes, edges, variables, schedule}
    # 5. Validate output, retry with feedback if invalid
```

### template_library.py — 6 Built-in Templates
1. **Real Estate Market Analysis** — WebSearch → PropertyResearch → DataAnalysis → VoiceCalls → Report. Variables: location, price_range, property_type
2. **Competitive Intelligence** — WebSearch(competitor) → WebScrape(pricing) → WebScrape(features) → WebSearch(reviews) → Compare → Report. Variables: competitor_names, your_product
3. **Local Business Survey** — GooglePlaces(type, area) → WebScrape(each) → VoiceCalls(gaps) → Merge → Analyze → Report. Variables: business_type, area, questions
4. **Due Diligence** — parallel WebSearches (company, leadership, financials, lawsuits, reviews) → Synthesize → Report. Variables: company_name
5. **Price Monitor** — Schedule(daily) → WebScrape(urls) → Compare(previous) → Alert(if_changed). Variables: urls, frequency
6. **People Research** — WebSearch(person) → WebSearch(social) → WebSearch(professional) → Synthesize → Report. Variables: person_name, context

---

## API ROUTES

**`/api/workflows`**: POST / (create), GET / (list for project), GET /{id}, PUT /{id}, DELETE /{id}, POST /{id}/activate, POST /{id}/pause, POST /{id}/run (trigger), GET /{id}/runs, GET /{id}/runs/{run_id} (with node results).

**`/api/workflows/from-template`**: POST / — {template_id, variables, project_id}

**`/api/workflows/from-description`**: POST / — {description, project_id} → returns generated workflow for review

**`/api/workflow-templates`**: GET / (list system + custom), GET /{id} (with variables_schema), POST / (create from existing workflow)

---

## FRONTEND

### Visual Workflow Editor (`/projects/[id]/workflows/[id]`)
Use **reactflow** (npm: reactflow) for the node editor:
- **Left sidebar**: draggable node palette, organized by category (Research, Data, Analysis, Output, Control)
- **Center canvas**: place and connect nodes. Each node shows icon + name + config summary + I/O ports
- **Right sidebar**: properties panel for selected node — configure all node-specific settings
- **Toolbar**: Save, Validate, Run, Export
- **Run mode**: nodes show live status (green/yellow/red/gray), click to see output

### NL Workflow Creator
Prominent text input on workflow creation page:
```
Describe your workflow: [___________________________________________] [Generate]
```
Shows generated workflow in visual editor for review before saving.

### Workflow Run View
Node graph with live status during execution. Click any node to see its output. Timeline sidebar.

---

## SUCCESS CRITERIA (Agent 7 Checks)

- [ ] Workflow, WorkflowRun, WorkflowTemplate models with migrations
- [ ] All node types (25+) defined with config schemas and handlers
- [ ] WorkflowExecutor traverses DAG and executes nodes
- [ ] NLWorkflowBuilder converts natural language → workflow via Gemini
- [ ] 6 built-in templates with variable schemas
- [ ] Template instantiation works
- [ ] API routes for CRUD, activation, runs, templates, NL generation
- [ ] Frontend: visual node editor with reactflow
- [ ] Frontend: NL workflow creation
- [ ] Frontend: run view with live node status
- [ ] Celery tasks + Celery Beat for scheduled workflows
- [ ] docs/PHASE_3_PROGRESS.md updated
