# Phase 3 — Workflow Engine Progress

## Success Criteria

- [x] Workflow, WorkflowRun, WorkflowTemplate models with migrations
- [x] All node types (27) defined with config schemas and handlers
- [x] WorkflowExecutor traverses DAG and executes nodes
- [x] NLWorkflowBuilder converts natural language -> workflow via Gemini
- [x] 6 built-in templates with variable schemas
- [x] Template instantiation works
- [x] API routes for CRUD, activation, runs, templates, NL generation
- [x] Frontend: visual node editor with reactflow
- [x] Frontend: NL workflow creation
- [x] Frontend: run view with live node status
- [x] APScheduler integration for scheduled workflows
- [x] docs/PHASE_3_PROGRESS.md updated

## Architecture

### Backend

| Component | File | Description |
|-----------|------|-------------|
| Workflow model | `models/workflow.py` | UUID PK, JSONB nodes/edges/variables, status, trigger |
| WorkflowRun model | `models/workflow_run.py` | JSONB node_results, output_data, error |
| WorkflowTemplate model | `models/workflow_template.py` | JSONB nodes/edges templates, variables_schema |
| Migration | `alembic/versions/009_add_workflows.py` | Creates all 3 tables |
| Schemas | `schemas/workflow.py` | All Pydantic request/response models |
| Node Registry | `services/workflow/node_registry.py` | 27 node types with config schemas |
| Node Handlers | `services/workflow/node_handlers.py` | Async execution handlers for all nodes |
| Executor | `services/workflow/executor.py` | DAG topological sort + execution |
| Service | `services/workflow/service.py` | CRUD, validation, template instantiation |
| NL Builder | `services/workflow/nl_builder.py` | Gemini NL-to-workflow conversion |
| Templates | `services/workflow/templates.py` | 6 system templates |
| API Routes | `api/workflows.py` | Full CRUD + activate/run/validate |
| Template Routes | `api/workflow_templates.py` | List/get/create templates |
| Scheduler | `services/scheduler.py` | Workflow schedule support |

### Frontend

| Component | File | Description |
|-----------|------|-------------|
| Workflow List | `app/workflows/page.tsx` | Grid view of user's workflows |
| Create Workflow | `app/workflows/new/page.tsx` | Template/NL/blank creation |
| Visual Editor | `app/workflows/[id]/page.tsx` | reactflow canvas + sidebar panels |
| Run View | `app/workflows/[id]/runs/[runId]/page.tsx` | Live status visualization |
| Custom Node | `components/workflow/nodes/CustomNode.tsx` | Category-styled node |
| Run Status Node | `components/workflow/nodes/RunStatusNode.tsx` | Status-colored node |
| Node Palette | `components/workflow/NodePalette.tsx` | Draggable node sidebar |
| Properties Panel | `components/workflow/PropertiesPanel.tsx` | Node config editor |
| Toolbar | `components/workflow/WorkflowToolbar.tsx` | Save/Validate/Run/Activate |

### Node Types (27)

| Category | Count | Types |
|----------|-------|-------|
| Trigger | 3 | manual_trigger, schedule_trigger, webhook_trigger |
| Research | 5 | web_search, api_query, web_scrape, voice_call, expert_research |
| Data | 6 | filter, transform, merge, deduplicate, sort, aggregate |
| Analysis | 3 | ai_analyze, compare, trend_detect |
| Output | 6 | generate_report, generate_chart, export_data, send_email, send_alert, save_findings |
| Control | 4 | condition, loop, delay, human_review |

### Templates (6)

1. Real Estate Market Analysis
2. Competitive Intelligence
3. Local Business Survey
4. Due Diligence
5. Price Monitor
6. People Research
