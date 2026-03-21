# AGENT 4 — Live Dashboard & Monitoring System

## YOUR MISSION

You are a Claude Code agent. Build **Part A: the real-time birds-eye dashboard** showing all agents working across all projects, and **Part B: the monitoring/alerting system** for ongoing watchers.

**Start:** `/plan Read this entire file, explore existing WebSocket/Scout code, then build everything.`

---

## PART A: LIVE DASHBOARD

A real-time command center showing ALL active research:

```
┌─────────────────────────────────────────────────────────────────┐
│  AGENTARY COMMAND CENTER                         [3 Active Now] │
├─────────────────────────────────────────────────────────────────┤
│  ┌─ PROJECT: Austin Real Estate ─────────────────────────────┐  │
│  │  Mission: Housing market 78704                             │  │
│  │  🔍✅ → 🏠⏳ → 📞🟡 → 🧠⬜ → 📝⬜  (12 findings)       │  │
│  │  Latest: "Median $485k, up 3.2% QoQ" (conf: 0.92)        │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌─ LIVE ACTIVITY FEED ──────────────────────────────────────┐  │
│  │  10:42 🔍 Searching "Austin 78704 new construction 2024"  │  │
│  │  10:42 📊 Calculated: avg price/sqft = $312 (n=47)        │  │
│  │  10:41 📞 Call connected: Realty Austin (512) 555-1234     │  │
│  │  10:41 🧠 "Price trend suggests cooling market..."        │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌─ MONITORS ─────────────────────────────────────────────────┐ │
│  │  🟢 Austin prices — no change  │  🔴 Competitor X — ALERT │ │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### WebSocket Architecture

Build on existing Scout WebSocket. The flow:
```
Service emits Event (core/events.py) → Handler publishes to Redis → WebSocket Manager subscribes → Broadcasts to connected clients (filtered by user/project)
```

### websocket_manager.py
- `connect(ws, user_id, project_id=None)` — accept, register
- `disconnect(ws, user_id)` — remove
- `broadcast_event(event)` — route to relevant clients (project-scoped → project subscribers, user-scoped → that user, global → all)
- `subscribe_to_redis()` — subscribe to Redis pub/sub, forward to WebSocket clients

### redis_bridge.py
- `publish_event(event)` — publish to Redis channel `agentary:events:{project_id|global}`
- `subscribe_and_forward(ws_manager)` — subscribe and bridge to WebSocket

### WebSocket Endpoint
```python
@router.websocket("/ws/live-feed")
async def live_feed(websocket, token: str = Query(...)):
    # Auth via token, then:
    # Client sends: {"type": "subscribe", "project_id": "..."}
    # Server sends: all Event types filtered by subscription
```

Also: GET /api/live-feed/recent (polling fallback), GET /api/live-feed/active (active missions/workflows).

---

## PART B: MONITORING SYSTEM

### monitor.py model
Fields: id (UUID PK), project_id (FK projects), user_id (FK users), name (str 255), description (Text), monitor_type (str: web_content|api_data|price_tracker|listing_watcher|competitor_tracker|custom), status (str: active|paused|archived), check_config (JSONB — type-specific: url+selectors for web, criteria for listings, etc.), alert_config (JSONB: {channels: ["email", "dashboard"], template, recipients}), schedule_cron (str), timezone (str), last_check_at, last_change_at, last_snapshot (JSONB — previous result for comparison), total_checks (Int), total_alerts (Int), created_at, updated_at.

### alert.py model
Fields: id (UUID PK), monitor_id (FK monitors), project_id (FK projects), alert_type (str: change_detected|threshold_crossed|new_item|custom), title (str 500), message (Text), severity (str: info|warning|critical), data (JSONB: {old_value, new_value, field, source_url}), acknowledged (Bool default false), acknowledged_at, acknowledged_by (FK users nullable), delivered_channels (ARRAY String), created_at.

### monitor_service.py
- `create_monitor(user_id, data)` — create + register Celery Beat schedule
- `execute_check(monitor_id)` — run check, compare to last_snapshot, create alert if changed, update snapshot
- `detect_changes(monitor, new_data)` — compare to last_snapshot
- `send_alert(alert, monitor)` — deliver via email (Resend) + dashboard push

### change_detector.py
- `detect_text_change(old, new)` → diff
- `detect_value_change(old_val, new_val, threshold)` → change details
- `detect_new_items(old_list, new_list, key)` → new items
- `detect_removed_items(old_list, new_list, key)` → removed items

---

## API ROUTES

**Monitors**: POST /api/monitors, GET /api/monitors, GET /{id}, PUT /{id}, DELETE /{id}, POST /{id}/check (manual trigger), POST /{id}/pause, POST /{id}/resume, GET /{id}/alerts, GET /{id}/history.

**Alerts**: GET /api/alerts (filterable), PUT /api/alerts/{id}/acknowledge, GET /api/alerts/unread (count).

---

## FRONTEND PAGES

### `/dashboard` — Global Command Center
Components: Active Missions panel (crew status cards), Active Workflows panel (node progress), Live Activity Feed (scrolling log from WebSocket), Monitors panel (status indicators + recent alerts), Stats bar (findings today, active agents, alerts).

WebSocket: connect on mount, subscribe to all projects, update in real-time. Smooth animations (Framer Motion or CSS transitions). Auto-scroll feed, pause when user scrolls up.

### `/projects/[id]` — Project Dashboard
Same but scoped to one project.

### Monitors UI (`/projects/[id]/monitors`)
- List with status indicators (🟢 active, 🔴 alerting, ⏸️ paused)
- Create wizard: pick type → configure → schedule → alerts
- Detail: check history chart, alert history, current snapshot

### Alert Center
- Bell icon in header with unread badge
- Dropdown showing recent alerts
- Click → alert detail with change diff

---

## CELERY TASKS

```python
@celery_app.task(name="monitor.execute_check", queue="monitors")
def execute_monitor_check(monitor_id: str): ...

@celery_app.task(name="monitor.send_alert", queue="monitors")
def send_monitor_alert(alert_id: str): ...
```
Register each monitor's schedule with Celery Beat.

---

## SUCCESS CRITERIA (Agent 7 Checks)

- [ ] WebSocket /ws/live-feed working with auth
- [ ] WebSocketManager routes events to correct clients by project
- [ ] Redis pub/sub bridge for cross-process events
- [ ] Monitor and Alert models with migrations
- [ ] MonitorService: create, execute_check, detect_changes, send_alert
- [ ] ChangeDetector for text, value, list changes
- [ ] 5 monitor types configurable
- [ ] Alert via email (Resend) + dashboard push
- [ ] API routes for monitors, alerts, live-feed
- [ ] Frontend: /dashboard command center with real-time WebSocket updates
- [ ] Frontend: useWebSocket hook with reconnection
- [ ] Frontend: live activity feed with animations
- [ ] Frontend: monitor management + alert center
- [ ] Celery Beat for scheduled checks
- [ ] docs/PHASE_4_PROGRESS.md updated
