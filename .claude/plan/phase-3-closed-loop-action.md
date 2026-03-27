# Implementation Plan: Phase 3 — Closed-Loop Action

## Task Type
- [x] Backend (models, services, tasks, API endpoints)
- [x] Frontend (approval inbox, action history, operator console)
- [x] Fullstack (action lifecycle spans backend execution + frontend approval UX)

## Technical Solution

Phase 3 turns intelligence into bounded operations via a 4-model action architecture:
**Recommendation → ActionRequest → (PolicyEngine gate) → ActionExecution → ActionOutcome → Signal (feedback loop)**

The key insight: actions are NOT direct function calls. They are typed request objects that flow through a policy engine, optional approval queue, execution worker, and outcome recorder — creating a fully auditable, governable action pipeline.

**What exists (from Phase 2):**
- Recommendation model with accept/reject/acted_on status
- Recommendation inbox page with accept/reject UI
- Signal pipeline that feeds the intelligence layer
- 11 Celery task queues, beat scheduler, worker infrastructure
- Entity merge with undo support
- Existing policies model (basic CRUD)

**What Phase 3 adds:**
- 4 new models: ActionRequest, ActionPolicy, ActionExecution, ActionOutcome
- PolicyEngine that evaluates rules to gate actions
- 9 action handlers (one per action type)
- ActionDispatcher Celery task
- Feedback loop: outcomes create Signals
- 3 new frontend pages: Approval Inbox, Action History, Operator Console

---

## Implementation Steps

### Wave 1: Foundation (Epic 3.1 + 3.2) — Critical Path

**Step 1.1: Action Domain Models** (backend only)
- Create `backend/app/models/action_request.py` — ActionRequest with ActionType, ActionRequestStatus enums, 17 columns
- Create `backend/app/models/action_policy.py` — ActionPolicy with rules JSONB, priority ordering
- Create `backend/app/models/action_execution.py` — ActionExecution with ExecutorType, ExecutionStatus enums
- Create `backend/app/models/action_outcome.py` — ActionOutcome with OutcomeType enum, feedback_signal_id FK
- Register all models in `__init__.py`
- Create Alembic migration + apply
- Create Pydantic schemas in `backend/app/schemas/actions.py`
- Expected: 4 new model files, 1 schema file, 1 migration

**Step 1.2: Action Service** (backend only)
- Create `backend/app/services/actions/action_service.py`:
  - `create_action_request()` — creates request, evaluates policy, auto-approves or queues
  - `approve()` — transitions pending_approval → approved → dispatches execution
  - `reject()` — transitions pending_approval → rejected with reason
  - `cancel()` — transitions pending/approved → cancelled
  - `get_pending()` — pending approvals for user
  - `list_actions()` — filtered list
- Create `backend/app/services/actions/__init__.py`
- Expected: 2 new files

**Step 1.3: Policy Engine** (backend only)
- Create `backend/app/services/actions/policy_engine.py`:
  - `PolicyEngine.evaluate(action_request) → PolicyDecision`
  - Load active policies for user/project sorted by priority
  - Match conditions: action_type, confidence_above, priority_in, entity_type_in
  - Return: {requires_approval, auto_approve, escalate_to, timeout_hours}
  - Default: require_approval if no policy matches
- Create seed script: `backend/app/services/actions/seed_policies.py`
  - 11 default policies (one per action type, matching blueprint table)
  - Call from app startup in main.py lifespan
- Expected: 2 new files, 1 main.py edit

**Step 1.4: Action API Endpoints** (backend only)
- Create `backend/app/api/actions.py`:
  - `POST /api/actions` — create action request (triggers policy eval)
  - `GET /api/actions` — list (filterable by status, type, project)
  - `GET /api/actions/{id}` — detail with execution/outcome
  - `PUT /api/actions/{id}/approve` — approve pending action
  - `PUT /api/actions/{id}/reject` — reject with reason
  - `PUT /api/actions/{id}/cancel` — cancel pending/approved action
  - `GET /api/actions/pending` — pending approvals for current user
- Register router in main.py
- Expected: 1 new file, 1 main.py edit

---

### Wave 2: Execution (Epic 3.3 + 3.6) — Critical Path

**Step 2.1: Action Handlers** (backend only)
- Create `backend/app/services/actions/handlers/` directory
- Create `__init__.py` with handler registry
- Create 9 handler files:
  - `update_status.py` — updates entity/insight/recommendation status fields
  - `send_alert.py` — creates Alert record + sends email via Resend
  - `trigger_workflow.py` — creates WorkflowRun via workflow service
  - `trigger_monitor.py` — triggers monitor check via monitor service
  - `create_task.py` — creates internal task record (new simple Task model or use existing)
  - `generate_report.py` — triggers report generation via report service
  - `queue_call.py` — creates voice extraction call via voice service
  - `merge_entities.py` — calls entity merge_entities_enhanced
  - `escalate.py` — creates high-priority alert + sends notification
- Each handler: `async execute(action_request, db) → dict` returning result + side_effects
- Expected: 10 new files

**Step 2.2: Action Dispatcher Celery Task** (backend only)
- Create `backend/app/tasks/action_tasks.py`:
  - `dispatch_action(action_request_id)` task
  - Creates ActionExecution record (status=running)
  - Routes to appropriate handler based on action_type
  - On success: creates ActionExecution (completed) + ActionOutcome (success)
  - On failure: creates ActionExecution (failed) + ActionOutcome (failure)
  - Creates feedback Signal from outcome
- Add `actions` queue to celery_app.py routing
- Expected: 1 new file, 1 celery edit

**Step 2.3: Outcome Feedback Loop** (backend only)
- Create `backend/app/services/actions/outcome_service.py`:
  - `record_outcome()` — creates ActionOutcome
  - If success: creates Signal(source_type=action_outcome), updates recommendation status to acted_on, boosts entity confidence +0.05
  - If failure: logs, keeps recommendation as pending for retry, creates alert
  - If rejected_by_user: records rejection reason, Signal(type=user_flagged) as negative feedback
- Track metrics: acceptance rate, success rate by action type
- Expected: 1 new file

**Step 2.4: WebSocket Events for Actions** (backend only)
- Add to `backend/app/core/events.py`:
  - `action_pending_approval = "action.pending_approval"`
  - `action_approved = "action.approved"`
  - `action_executed = "action.executed"`
  - `action_failed = "action.failed"`
- Emit from action_service and action_tasks
- Expected: 1 file edit

---

### Wave 3: Frontend (Epic 3.4 + 3.5)

**Step 3.1: Types and API Client** (frontend only)
- Add to `dashboard/lib/types.ts`:
  - ActionRequest, ActionPolicy, ActionExecution, ActionOutcome interfaces
  - ActionType, ActionRequestStatus, OutcomeType type unions
- Add to `dashboard/lib/api.ts`:
  - `fetchActions()`, `fetchPendingActions()`, `fetchActionDetail()`
  - `createAction()`, `approveAction()`, `rejectAction()`, `cancelAction()`
- Expected: 2 file edits

**Step 3.2: Approval Inbox Page** (frontend only)
- Create `dashboard/app/approvals/page.tsx`:
  - List of pending action requests sorted by priority then age
  - Each card: action type icon, title, entity name, confidence bar, evidence count, time pending
  - Timeout indicator (approaching expiry)
  - Approve / Reject buttons
  - Click card → expand with: what (action description), why (linked recommendation + rationale), evidence chain, confidence meter
  - Reject modal with reason textarea
  - Bulk approve for low-risk batch
  - WebSocket subscription for new pending actions
- Expected: 1 new file

**Step 3.3: Action History Page** (frontend only)
- Create `dashboard/app/actions/page.tsx`:
  - Tabs: All / Completed / Failed / Rejected
  - Filter by: action type, date range, entity
  - Each row: type, title, status badge, outcome, execution time, timestamp
  - Click → detail with full execution + outcome + audit trail
- Expected: 1 new file

**Step 3.4: Operator Console Page** (frontend only)
- Create `dashboard/app/operator/page.tsx`:
  - 6 operational panels:
    1. **Pending Approvals** — count + urgency indicator + link to /approvals
    2. **Failed Actions (24h)** — list with retry buttons
    3. **Stale Recommendations** — count of recommendations needing refresh
    4. **Queue Health** — Celery queue depths + worker status (from /health)
    5. **Connector Health** — circuit breaker states (from /health)
    6. **Recent Escalations** — high-priority alerts
  - Auto-refresh every 30s
  - WebSocket for real-time updates
- Expected: 1 new file

**Step 3.5: Nav Updates** (frontend only)
- Add nav items: Approvals (bell icon) → /approvals, Operator (terminal icon) → /operator
- Add pending approval badge count (from /api/actions/pending count)
- Expected: 1 file edit

**Step 3.6: Integrate "Take Action" into Recommendations** (frontend only)
- Enhance `dashboard/app/recommendations/page.tsx`:
  - Add "Take Action" button on accepted recommendations
  - Opens action creation modal: pre-fills from recommendation.suggested_action
  - On submit: POST /api/actions with recommendation_id
  - Shows action status after creation
- Expected: 1 file edit

---

### Wave 4: Testing + Verification

**Step 4.1: Policy Engine Unit Tests**
- Test each default policy
- Test policy priority ordering
- Test no-match default (require_approval)
- Test confidence threshold conditions

**Step 4.2: Action Lifecycle Integration Test**
- Create action → policy eval → auto-approve → execute → outcome → signal
- Create action → policy eval → require_approval → approve → execute → outcome
- Create action → reject → verify recommendation stays pending

**Step 4.3: Update Blueprint**
- Mark all Phase 3 epics as COMPLETE
- Check Phase 3 readiness rubric

---

## Key Files

| File | Operation | Description |
|------|-----------|-------------|
| `backend/app/models/action_request.py` | Create | ActionRequest model with ActionType, ActionRequestStatus |
| `backend/app/models/action_policy.py` | Create | ActionPolicy model with JSONB rules |
| `backend/app/models/action_execution.py` | Create | ActionExecution model |
| `backend/app/models/action_outcome.py` | Create | ActionOutcome model with feedback_signal_id |
| `backend/app/schemas/actions.py` | Create | Pydantic schemas for all action models |
| `backend/app/services/actions/action_service.py` | Create | Core action CRUD + lifecycle |
| `backend/app/services/actions/policy_engine.py` | Create | Policy evaluation engine |
| `backend/app/services/actions/seed_policies.py` | Create | Default policy seeding |
| `backend/app/services/actions/outcome_service.py` | Create | Outcome recording + feedback loop |
| `backend/app/services/actions/handlers/*.py` | Create | 9 action type handlers |
| `backend/app/tasks/action_tasks.py` | Create | ActionDispatcher Celery task |
| `backend/app/api/actions.py` | Create | 7 action API endpoints |
| `backend/app/core/events.py` | Modify | Add action event types |
| `backend/app/celery_app.py` | Modify | Add actions queue routing |
| `backend/app/main.py` | Modify | Register actions router, seed policies |
| `backend/app/models/__init__.py` | Modify | Register action models |
| `dashboard/lib/types.ts` | Modify | Add action TypeScript types |
| `dashboard/lib/api.ts` | Modify | Add action API functions |
| `dashboard/app/approvals/page.tsx` | Create | Approval inbox page |
| `dashboard/app/actions/page.tsx` | Create | Action history page |
| `dashboard/app/operator/page.tsx` | Create | Operator console page |
| `dashboard/app/recommendations/page.tsx` | Modify | Add "Take Action" button |
| `dashboard/components/Nav.tsx` | Modify | Add Approvals + Operator nav items |

## Risks and Mitigation

| Risk | Mitigation |
|------|------------|
| Auto-execute safety: runaway policy approves destructive actions | Default ALL policies to require_approval. Only 5 types auto-approve (send_alert, trigger_monitor, create_task, generate_report, escalate). No auto-approve for merge, calls, workflows. |
| Feedback loop creates infinite signals | Cap: max 1 outcome signal per action. Don't re-process outcome signals into new recommendations. |
| Handler failure leaves orphaned ActionExecution | Wrap each handler in try/finally. On crash: mark execution as failed, create failure outcome. |
| Approval timeout: actions expire unnoticed | Celery Beat task: check for expired pending actions daily. Create alert for operator. |
| Operator console data overload | Pagination + time windows (last 24h defaults). Lazy-load panels. |

## Sequencing and Dependencies

```
Wave 1 (foundation):
  Step 1.1 (models) ──┐
  Step 1.2 (service)   ├── all independent, can parallel
  Step 1.3 (policy)    │
  Step 1.4 (API)  ─────┘

Wave 2 (execution) — depends on Wave 1:
  Step 2.1 (handlers) ─┬── independent of each other
  Step 2.2 (dispatcher)│
  Step 2.3 (outcomes)  │
  Step 2.4 (events) ───┘

Wave 3 (frontend) — depends on Wave 1+2:
  Step 3.1 (types/api) → Step 3.2-3.6 (all pages independent)

Wave 4 (testing) — depends on all above
```

## SESSION_ID
- CODEX_SESSION: N/A (external models not available)
- GEMINI_SESSION: N/A (external models not available)
