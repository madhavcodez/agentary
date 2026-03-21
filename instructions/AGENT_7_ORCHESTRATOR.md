# AGENT 7 — Orchestrator (Integration, QA & Continuous Improvement)

## YOUR MISSION

You are the **orchestrator agent**. Your job is different from Agents 0-6. You:

1. **Monitor progress** of all other agents
2. **Verify their work** against success criteria
3. **Integrate their outputs** — make sure everything connects
4. **Fix integration issues** — resolve conflicts, broken imports, missing wiring
5. **Run end-to-end tests** — verify the full platform works as one system
6. **Iterate endlessly** — keep improving until everything is solid

You run LAST (or in parallel, checking periodically). You never stop. When you run out of issues, you add tests, improve code quality, and optimize.

**Start by running:** `/plan Read this entire file. Then check what all other agents have built. Then start verifying and integrating.`

---

## YOUR OPERATING LOOP

```
while true:
    1. Check all PHASE_*_PROGRESS.md files
    2. Run the full test suite
    3. Try to build (backend + frontend + docker)
    4. Try to start the full system
    5. For each phase, verify success criteria
    6. Fix any issues found
    7. Wire together anything that's disconnected
    8. Run end-to-end integration tests
    9. Improve test coverage
    10. Optimize, refactor, document
    11. Go back to step 1
```

---

## PHASE-BY-PHASE VERIFICATION CHECKLIST

### Phase 0: Foundation
```bash
# Check no old domain references remain
grep -rn "SecretAIRY\|secretairy\|Opportunity\|Dossier\|match_engine\|dossier_gen\|outreach_gen\|pipeline_engine" \
  --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" \
  backend/ frontend/ | grep -v node_modules | grep -v __pycache__ | grep -v .git

# Check critical files exist
test -f backend/app/core/events.py && echo "✅ events.py" || echo "❌ events.py MISSING"
test -f backend/app/core/feature_flags.py && echo "✅ feature_flags.py" || echo "❌ MISSING"
test -f backend/app/tasks/celery_app.py && echo "✅ celery_app.py" || echo "❌ MISSING"
test -f docs/RENAME_MAP.md && echo "✅ RENAME_MAP.md" || echo "❌ MISSING"
test -f docs/PHASE_0_PROGRESS.md && echo "✅ progress" || echo "❌ MISSING"

# Check models exist
for model in project mission expert_agent agent_crew crew_run crew_task finding research_result \
  voice_session workflow workflow_template report monitor alert entity data_source; do
  test -f backend/app/models/${model}.py && echo "✅ ${model}.py" || echo "❌ ${model}.py MISSING"
done

# Check migrations
ls backend/alembic/versions/ | tail -5

# Check frontend builds
cd frontend && npm run build 2>&1 | tail -20

# Check docker builds
docker compose build 2>&1 | tail -20
```

### Phase 1: Research Engine
```bash
# Check expert agents exist
grep -l "BUILTIN_EXPERTS\|expert_registry" backend/app/services/crews/ 2>/dev/null
python -c "from app.services.crews.expert_registry import ExpertRegistry; print('✅ ExpertRegistry imports')" 2>&1

# Check crew runner
grep -l "class CrewRunner" backend/app/services/crews/ 2>/dev/null
grep -l "execute_run" backend/app/services/crews/crew_runner.py 2>/dev/null

# Check tool registry
grep -l "class ToolRegistry" backend/app/services/crews/ 2>/dev/null

# Check API routes
grep -rn "router.*missions\|router.*crews\|router.*experts" backend/app/api/routes/ 2>/dev/null

# Check Celery tasks
grep -l "crew.execute_run" backend/app/tasks/ 2>/dev/null
```

### Phase 2: Voice Extraction
```bash
# Check voice service
grep -l "class VoiceService" backend/app/services/voice/ 2>/dev/null
grep -l "class ExtractionService" backend/app/services/voice/ 2>/dev/null
grep -l "class CallScriptGenerator" backend/app/services/voice/ 2>/dev/null

# Check Twilio integration
grep -l "twilio\|pipecat\|media_stream" backend/app/services/voice/ 2>/dev/null

# Check extraction templates
grep -l "ExtractionTemplate\|BUILTIN_TEMPLATES" backend/ -r 2>/dev/null
```

### Phase 3: Workflow Engine
```bash
# Check workflow executor
grep -l "class WorkflowExecutor" backend/app/services/workflows/ 2>/dev/null
grep -l "class NLWorkflowBuilder" backend/app/services/workflows/ 2>/dev/null

# Check node types
grep -c "node_type\|NODE_TYPE" backend/app/services/workflows/ -r 2>/dev/null

# Check templates
grep -l "WorkflowTemplate\|template_library" backend/app/services/workflows/ 2>/dev/null

# Check frontend workflow editor
find frontend/ -name "*.tsx" -path "*workflow*" 2>/dev/null
```

### Phase 4: Live Dashboard & Monitoring
```bash
# Check WebSocket
grep -l "websocket\|WebSocket" backend/app/api/routes/live_feed.py 2>/dev/null
grep -l "class WebSocketManager" backend/app/services/live_feed/ 2>/dev/null

# Check Redis bridge
grep -l "redis.*publish\|Redis.*Bridge" backend/app/services/live_feed/ 2>/dev/null

# Check monitoring
grep -l "class MonitorService" backend/app/services/monitoring/ 2>/dev/null
grep -l "class ChangeDetector" backend/app/services/monitoring/ 2>/dev/null

# Check frontend dashboard
find frontend/ -name "*.tsx" -path "*dashboard*" 2>/dev/null
```

### Phase 5: Data Sources
```bash
# Check connector count
find backend/app/services/data_sources/connectors/ -name "*.py" | wc -l

# Check registry
grep -l "class SourceRegistry" backend/app/services/data_sources/ 2>/dev/null

# Check entity service
grep -l "class EntityService" backend/app/services/entities/ 2>/dev/null
```

### Phase 6: Reports & Export
```bash
# Check report generator
grep -l "class ReportGenerator" backend/app/services/reports/ 2>/dev/null
grep -l "class PDFExporter" backend/app/services/reports/ 2>/dev/null
grep -l "class ChartGenerator" backend/app/services/reports/ 2>/dev/null
grep -l "class DataExporter" backend/app/services/reports/ 2>/dev/null

# Check share service
grep -l "class ShareService\|share_token" backend/app/services/reports/ 2>/dev/null
```

---

## INTEGRATION TASKS

Once you've verified each phase, wire everything together:

### 1. Main App Router Registration
Ensure ALL route modules are registered in the FastAPI app:
```python
# backend/app/main.py or app/api/__init__.py
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(missions_router)
app.include_router(crews_router)
app.include_router(experts_router)
app.include_router(voice_router)
app.include_router(workflows_router)
app.include_router(reports_router)
app.include_router(monitors_router)
app.include_router(alerts_router)
app.include_router(entities_router)
app.include_router(data_sources_router)
app.include_router(live_feed_router)
app.include_router(analytics_router)
app.include_router(export_router)
```

### 2. Model Registration
Ensure ALL models are imported for Alembic to discover:
```python
# backend/app/models/__init__.py
from .user import User
from .project import Project
from .mission import Mission
from .expert_agent import ExpertAgent
from .agent_crew import AgentCrew
from .crew_run import CrewRun
from .crew_task import CrewTask
from .finding import Finding
from .research_result import ResearchResult
from .voice_session import VoiceSession
from .extraction_template import ExtractionTemplate
from .workflow import Workflow
from .workflow_template import WorkflowTemplate
from .workflow_run import WorkflowRun
from .report import Report
from .monitor import Monitor
from .alert import Alert
from .entity import Entity
from .entity_collection import EntityCollection
from .data_source import DataSource
from .audit_log import AuditLog
```

### 3. Event Bus Wiring
Connect the event bus to:
- Redis pub/sub (for cross-process delivery to WebSockets)
- Audit log writer (persist all events)
- Analytics counters (increment metrics)

### 4. Celery Task Discovery
Ensure all task modules are discovered:
```python
# backend/app/tasks/celery_app.py
celery_app.autodiscover_tasks([
    "app.tasks.crew_runs",
    "app.tasks.research_tasks",
    "app.tasks.voice_tasks",
    "app.tasks.report_tasks",
    "app.tasks.monitor_tasks",
    "app.tasks.workflow_tasks",
])
```

### 5. Source Registry Initialization
On app startup, initialize the source registry with all connectors and register it as a dependency.

### 6. Expert Registry Initialization
On first startup, seed all built-in expert agents into the database.

### 7. Frontend API Client
Ensure frontend has API client functions for ALL endpoints:
```typescript
// frontend/lib/api/index.ts
export * from './projects'
export * from './missions'
export * from './crews'
export * from './voice'
export * from './workflows'
export * from './reports'
export * from './monitors'
export * from './entities'
export * from './data-sources'
```

### 8. Frontend Navigation
Update the sidebar/nav to include all pages:
- Dashboard (command center)
- Projects (list + detail)
- Live Feed
- Reports
- Settings

### 9. Docker Compose Services
Ensure all services are defined:
```yaml
services:
  agentary-api:        # FastAPI
  agentary-frontend:   # Next.js
  agentary-db:         # PostgreSQL
  agentary-redis:      # Redis
  agentary-qdrant:     # Qdrant vector DB
  agentary-celery:     # Celery worker (all queues)
  agentary-beat:       # Celery beat scheduler
```

---

## END-TO-END TEST SCENARIOS

Write and run these integration tests:

### Test 1: Create Project and Mission
```
1. Create user (or use existing)
2. Create project "Gas Station Survey"
3. Create mission "Find gas prices within 5 miles of 30.2672, -97.7431"
4. Verify project and mission in database
5. Verify API returns correct data
```

### Test 2: Research Execution
```
1. Start mission from Test 1
2. Verify crew is assembled with appropriate experts
3. Verify CrewRun is created
4. Verify tasks are created for each expert
5. Execute (with mocked external APIs)
6. Verify findings are generated
7. Verify events are emitted
```

### Test 3: Report Generation
```
1. Using findings from Test 2
2. Generate a research report
3. Verify report has sections, sources, charts
4. Export as PDF
5. Create share link
6. Verify shared report is accessible without auth
```

### Test 4: Workflow Execution
```
1. Create workflow from template
2. Execute workflow
3. Verify each node executes in order
4. Verify final output
```

### Test 5: Monitor and Alert
```
1. Create a monitor
2. Simulate a change in monitored data
3. Verify alert is generated
4. Verify notification is sent
```

### Test 6: Full Golden Path
```
1. User signs up
2. Creates project "Austin Real Estate Research"
3. Creates mission "Analyze housing market in 78704"
4. System assembles crew: WebResearcher, PropertyResearcher, DataAnalyst, Synthesizer, ReportWriter
5. Crew executes (mocked APIs return realistic data)
6. 30+ findings generated across experts
7. Report generated with charts and analysis
8. Monitor set up for new listings
9. Data exported as CSV
10. Verify entire flow end-to-end
```

---

## CONTINUOUS IMPROVEMENT LOOP

After integration is solid, iterate on:

1. **Code Quality**
   - Add type hints everywhere
   - Fix any linting issues
   - Ensure consistent error handling
   - Add docstrings to all public methods

2. **Test Coverage**
   - Unit tests for all services
   - Integration tests for API routes
   - Model tests for all database operations

3. **Performance**
   - Add database indexes where needed
   - Optimize N+1 queries
   - Add caching for expensive operations

4. **Documentation**
   - API documentation (auto-generated from FastAPI)
   - Architecture diagram updates
   - Setup/deployment guide

5. **Error Handling**
   - Graceful degradation when external APIs fail
   - User-friendly error messages
   - Retry logic for transient failures

6. **Security**
   - Input validation on all endpoints
   - SQL injection prevention (already covered by SQLAlchemy)
   - Rate limiting on public endpoints
   - API key encryption at rest

---

## SUCCESS CRITERIA

- [ ] All Phase 0-6 success criteria verified
- [ ] All routes registered in FastAPI app
- [ ] All models registered for Alembic
- [ ] Event bus connected to Redis and WebSocket
- [ ] All Celery tasks discoverable
- [ ] Source registry initialized on startup
- [ ] Expert registry seeded on startup
- [ ] Frontend navigation complete
- [ ] Docker Compose starts all 7 services
- [ ] 6 end-to-end test scenarios pass
- [ ] No broken imports or circular dependencies
- [ ] `alembic upgrade head` runs cleanly
- [ ] `npm run build` succeeds
- [ ] API docs accessible at /docs
- [ ] Zero critical errors in logs on startup
