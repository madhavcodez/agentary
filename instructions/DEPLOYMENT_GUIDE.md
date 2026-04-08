# DEPLOYMENT GUIDE — How to Run All 8 Agents Overnight

## Overview

You will run **8 coding-agent CLI terminals** in parallel, each working on a different phase of Agentary. They'll run all night on 2x usage with max effort.
In all commands below, replace `agent-cli` with your installed coding CLI command.

```
Terminal 0: Agent 0 — Foundation & Domain Rename     (STARTS FIRST — 30min head start)
Terminal 1: Agent 1 — Research Engine & Expert Crews  (starts after ~30min)
Terminal 2: Agent 2 — Voice Extraction System         (starts after ~30min)
Terminal 3: Agent 3 — Workflow Engine                  (starts after ~30min)
Terminal 4: Agent 4 — Live Dashboard & Monitoring      (starts after ~30min)
Terminal 5: Agent 5 — Data Sources & Connectors        (starts after ~30min)
Terminal 6: Agent 6 — Reports & Export                 (starts after ~30min)
Terminal 7: Agent 7 — Orchestrator                     (starts after ~2hrs)
```

---

## Prerequisites

1. **coding-agent CLI installed** with your API key configured
2. **The SecretAIRY repo** cloned locally
3. **Docker + Docker Compose** installed
4. **Node.js 18+** installed
5. **Python 3.11+** installed
6. **tmux or multiple terminal tabs** (tmux recommended for overnight)

---

## Step 1: Prepare the Repo

```bash
# Clone if needed
cd ~/projects/agentary  # or wherever your repo is

# Make sure the repo is clean
git checkout main
git pull
git status  # should be clean

# Create a working branch
git checkout -b feat/agentary-pivot

# Create the agent instructions directory IN the repo
mkdir -p docs/agent-instructions
```

---

## Step 2: Copy Agent Instructions Into the Repo

Copy all 8 AGENT_*.md files into `docs/agent-instructions/` in your repo. Each agent needs to be able to read its own instructions.

```bash
# Copy from wherever you saved them
cp /path/to/AGENT_0_FOUNDATION.md docs/agent-instructions/
cp /path/to/AGENT_1_RESEARCH_ENGINE.md docs/agent-instructions/
cp /path/to/AGENT_2_VOICE_EXTRACTION.md docs/agent-instructions/
cp /path/to/AGENT_3_WORKFLOW_ENGINE.md docs/agent-instructions/
cp /path/to/AGENT_4_LIVE_DASHBOARD.md docs/agent-instructions/
cp /path/to/AGENT_5_DATA_SOURCES.md docs/agent-instructions/
cp /path/to/AGENT_6_REPORTS_EXPORT.md docs/agent-instructions/
cp /path/to/AGENT_7_ORCHESTRATOR.md docs/agent-instructions/
```

---

## Step 3: Set Up tmux Sessions

```bash
# Create a tmux session with 8 windows
tmux new-session -s agentary -n agent0
tmux new-window -t agentary -n agent1
tmux new-window -t agentary -n agent2
tmux new-window -t agentary -n agent3
tmux new-window -t agentary -n agent4
tmux new-window -t agentary -n agent5
tmux new-window -t agentary -n agent6
tmux new-window -t agentary -n agent7
```

---

## Step 4: Launch Agent 0 FIRST (30-Minute Head Start)

Agent 0 renames the codebase and creates the directory structure. Other agents need this done first.

```bash
# In tmux window 0
tmux select-window -t agentary:agent0

# Navigate to repo
cd ~/projects/agentary

# Launch Agent 0
agent-cli --dangerously-skip-permissions

# Once coding-agent CLI is open, paste:
/plan Read docs/agent-instructions/AGENT_0_FOUNDATION.md completely. Then explore the entire repo structure. Then execute every step in the file end-to-end. Do not stop until every success criteria is met. After completing all steps, loop back and verify everything, fixing any issues found. Keep iterating until perfect.
```

**Wait ~30 minutes** for Agent 0 to set up the basic structure before launching others.

---

## Step 5: Launch Agents 1-6 (After Agent 0 Has Head Start)

In each tmux window, launch the corresponding agent:

### Terminal 1 — Research Engine
```bash
tmux select-window -t agentary:agent1
cd ~/projects/agentary
agent-cli --dangerously-skip-permissions

# Paste:
/plan Read docs/agent-instructions/AGENT_1_RESEARCH_ENGINE.md completely. Explore what Agent 0 has set up so far. Then build the entire research engine and expert crew system end-to-end. Create all models, services, API routes, Celery tasks, and frontend pages. Do not stop until every success criteria is met. If Agent 0 hasn't created a directory you need yet, create it yourself. Keep iterating until perfect.
```

### Terminal 2 — Voice Extraction
```bash
tmux select-window -t agentary:agent2
cd ~/projects/agentary
agent-cli --dangerously-skip-permissions

# Paste:
/plan Read docs/agent-instructions/AGENT_2_VOICE_EXTRACTION.md completely. Explore the existing Pipecat + Gemini Live + Twilio voice code. Then build the voice extraction system end-to-end. Create all models, services, API routes, and frontend pages. Do not stop until every success criteria is met. Keep iterating until perfect.
```

### Terminal 3 — Workflow Engine
```bash
tmux select-window -t agentary:agent3
cd ~/projects/agentary
agent-cli --dangerously-skip-permissions

# Paste:
/plan Read docs/agent-instructions/AGENT_3_WORKFLOW_ENGINE.md completely. Then build the entire workflow engine end-to-end. Create all models, services (including the natural language workflow builder and visual editor), API routes, templates, and frontend pages. Do not stop until every success criteria is met. Keep iterating until perfect.
```

### Terminal 4 — Live Dashboard & Monitoring
```bash
tmux select-window -t agentary:agent4
cd ~/projects/agentary
agent-cli --dangerously-skip-permissions

# Paste:
/plan Read docs/agent-instructions/AGENT_4_LIVE_DASHBOARD.md completely. Explore the existing WebSocket/Scout code. Then build the live dashboard, WebSocket system, monitoring service, and alert system end-to-end. Create all models, services, API routes, and frontend pages. Do not stop until every success criteria is met. Keep iterating until perfect.
```

### Terminal 5 — Data Sources
```bash
tmux select-window -t agentary:agent5
cd ~/projects/agentary
agent-cli --dangerously-skip-permissions

# Paste:
/plan Read docs/agent-instructions/AGENT_5_DATA_SOURCES.md completely. Explore existing connectors (Exa, Gemini). Then build the entire data source connector system with all 10 connectors, the source registry, and the entity system. Create all models, services, API routes. Do not stop until every success criteria is met. Keep iterating until perfect.
```

### Terminal 6 — Reports & Export
```bash
tmux select-window -t agentary:agent6
cd ~/projects/agentary
agent-cli --dangerously-skip-permissions

# Paste:
/plan Read docs/agent-instructions/AGENT_6_REPORTS_EXPORT.md completely. Then build the report generation system, chart generator, PDF exporter, data exporter, and sharing service end-to-end. Create all models, services, API routes, and frontend pages. Do not stop until every success criteria is met. Keep iterating until perfect.
```

---

## Step 6: Launch Agent 7 (After ~2 Hours)

Wait until the other agents have made substantial progress before launching the orchestrator:

```bash
tmux select-window -t agentary:agent7
cd ~/projects/agentary
agent-cli --dangerously-skip-permissions

# Paste:
/plan Read docs/agent-instructions/AGENT_7_ORCHESTRATOR.md completely. Then check the progress of all other agents by examining the codebase, running tests, and verifying success criteria. Fix any integration issues, wire everything together, run end-to-end tests, and keep iterating until the entire platform works as one system. Never stop — keep finding and fixing issues, adding tests, and improving code quality.
```

---

## Step 7: Monitor Progress

Use tmux to switch between windows and check progress:

```bash
# Switch between agents
tmux select-window -t agentary:agent0  # Ctrl+B, 0
tmux select-window -t agentary:agent1  # Ctrl+B, 1
# ... etc

# Check progress files
cat docs/PHASE_0_PROGRESS.md
cat docs/PHASE_1_PROGRESS.md
# ... etc

# Check git log
git log --oneline -20

# Check for errors
grep -r "ERROR\|FAIL\|❌" docs/PHASE_*_PROGRESS.md
```

---

## Step 8: Morning Review

When you wake up:

1. **Check all progress files:**
```bash
for i in 0 1 2 3 4 5 6; do
  echo "=== Phase $i ==="
  cat docs/PHASE_${i}_PROGRESS.md 2>/dev/null || echo "Not found"
  echo
done
```

2. **Check if it builds:**
```bash
cd backend && python -c "from app.main import app; print('Backend OK')"
cd frontend && npm run build
docker compose build
```

3. **Check test results:**
```bash
cd backend && pytest -v --tb=short
```

4. **Launch the full system:**
```bash
docker compose up -d
# Check logs
docker compose logs -f --tail=50
```

---

## Handling Conflicts Between Agents

Multiple agents writing to the same repo WILL create conflicts. Mitigation:

1. **Each agent works in its own directories mostly:**
   - Agent 0: everywhere (but finishes first)
   - Agent 1: `services/crews/`, `models/mission.py`, `models/crew*.py`, `models/finding.py`
   - Agent 2: `services/voice/`, `models/voice*.py`
   - Agent 3: `services/workflows/`, `models/workflow*.py`
   - Agent 4: `services/live_feed/`, `services/monitoring/`, `models/monitor.py`, `models/alert.py`
   - Agent 5: `services/data_sources/`, `services/entities/`, `models/entity*.py`, `models/data_source.py`
   - Agent 6: `services/reports/`, `models/report.py`
   - Agent 7: integration files, tests, main.py

2. **Shared files that might conflict:**
   - `models/__init__.py` — Agent 7 manages this
   - `main.py` — Agent 7 manages this
   - `docker-compose.yml` — Agent 0 creates, Agent 7 updates
   - Migration files — each agent creates its own, Agent 7 resolves

3. **If an agent encounters a conflict:** it should `git stash`, `git pull`, `git stash pop`, resolve, continue.

---

## Tips for Overnight Success

1. **Make sure your machine won't sleep** — disable sleep/hibernate
2. **Plenty of disk space** — these agents generate a lot of code
3. **Stable internet** — needed for model API calls
4. **tmux keeps running** even if you close the terminal window
5. **Check logs periodically** if you're still awake — agents might get stuck
6. **Git auto-commit** — each agent commits frequently, so progress is saved
7. **If an agent seems stuck** — kill it and restart with the same /plan command. The coding agent will pick up where it left off by reading the codebase.
