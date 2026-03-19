<p align="center">
  <h1 align="center">SecretAIRY</h1>
  <p align="center">
    <strong>AI Chief-of-Staff that researches companies, finds contacts, and makes cold calls on your behalf.</strong>
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> &middot;
    <a href="#how-it-works">How It Works</a> &middot;
    <a href="#architecture">Architecture</a> &middot;
    <a href="#api-reference">API</a>
  </p>
</p>

---

SecretAIRY is an open-source AI secretary that automates the entire job outreach pipeline: it scrapes real job postings, scores them against your resume, deep-researches companies using web search, auto-discovers hiring contacts, generates personalized multi-channel outreach (cold calls, emails, LinkedIn messages), and executes calls via Twilio with a real-time Gemini Live voice agent.

**This is NOT a robocaller.** It's a relationship operating system with four modes: Scout, Shadow, Assistant, and Autopilot.

## Features

- **Resume Parsing** — Upload your resume, AI extracts structured skills, experience, preferences
- **Job Scouting** — Ingests real jobs from Greenhouse, Lever, and HN Who's Hiring APIs
- **AI Match Scoring** — Hard filters + vector similarity + LLM scoring (0-100 with rationale)
- **Deep Research** — Gemini with Google Search grounding researches companies (news, funding, leadership, culture)
- **Contact Discovery** — Exa API finds recruiters and hiring managers on LinkedIn automatically
- **OpenClaw Integration** — Browser automation for deep scraping career pages and LinkedIn profiles
- **Multi-Channel Outreach** — AI generates personalized call scripts, email drafts, and LinkedIn messages
- **Outbound Cold Calls** — Twilio + Pipecat + Gemini Live voice agent makes real phone calls
- **Full Autopilot** — Scheduled pipeline: ingest → score → research → find contacts → generate outreach → make calls
- **Policy Engine** — Business hours enforcement, daily call limits, forbidden topics, PII detection

## How It Works

```
1. UPLOAD RESUME ──→ AI parses skills, experience, preferences
                      │
2. SCOUT ──────────→ Scrape 500+ real jobs from Greenhouse, Lever, HN
                      │
3. MATCH ──────────→ Score every job: hard filters + semantic + LLM (0-100)
                      │
4. RESEARCH ───────→ For top matches:
                      ├── Gemini + Google Search → company news, funding, leadership
                      ├── Exa API → find recruiters on LinkedIn
                      └── OpenClaw → scrape career pages, org charts
                      │
5. OUTREACH ───────→ Generate personalized:
                      ├── Cold call script (opener, pitch points, voicemail)
                      ├── Email draft (unique per contact, references research)
                      └── LinkedIn message (300 char, connection request)
                      │
6. EXECUTE ────────→ Twilio dials the contact
                      ├── Pipecat handles real-time audio
                      ├── Gemini Live runs the conversation
                      └── Post-call: transcript, outcome classification, follow-ups
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Dashboard (Next.js 14)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐    │
│  │ Profile  │  │Job Search│  │ Matches  │  │      Outreach        │    │
│  │ Upload   │  │ Database │  │  Ranked  │  │ Networking│Cold Calls│    │
│  └──────────┘  └──────────┘  └──────────┘  │ Convos   │Ideas     │    │
│                                             └──────────────────────┘    │
└─────────────────────────────┬────────────────────────────────────────────┘
                              │ REST API
┌─────────────────────────────▼────────────────────────────────────────────┐
│                        FastAPI Backend                                    │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Profile   │  │   Ingest     │  │    Match     │  │   Research   │ │
│  │   Builder   │  │   Runner     │  │    Engine    │  │    Engine    │ │
│  │  (Gemini)   │  │ (GH/Lever/HN)│  │(Semantic+LLM)│  │(Gemini+Exa) │ │
│  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Outreach   │  │  Autopilot   │  │   Twilio     │  │   Pipecat    │ │
│  │  Generator  │  │ Orchestrator │  │   Client     │  │   Pipeline   │ │
│  │(Email+LI+Call)│ │ (Scheduler) │  │  (REST API)  │  │(Gemini Live) │ │
│  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Gemini 2.5 Flash                             │   │
│  │     Google Search Grounding │ Embeddings │ Native Audio (Live)   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└───────┬──────────────┬──────────────┬──────────────┬────────────────────┘
        │              │              │              │
   ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐   ┌────▼─────┐
   │Postgres │   │   Redis   │  │ Qdrant  │   │ OpenClaw │
   │  :5432  │   │   :6379   │  │  :6333  │   │ (browser │
   │         │   │           │  │ vectors │   │  scraper)│
   └─────────┘   └───────────┘  └─────────┘   └──────────┘
```

## Quick Start

### Prerequisites

- **Docker** — Postgres, Redis, Qdrant containers
- **Python 3.10+**
- **Node.js 18+**
- **API Keys** — Gemini (required), Twilio (for calls), Exa (for contact discovery)

### 1. Clone & Configure

```bash
git clone https://github.com/madhavcodez/SecretAIRY.git
cd SecretAIRY
cp .env.example .env
# Edit .env with your API keys
```

### 2. Infrastructure

```bash
# Start Postgres, Redis, Qdrant (if not already running)
docker run -d --name secretairy-postgres -e POSTGRES_USER=secretairy -e POSTGRES_PASSWORD=secretairy -e POSTGRES_DB=secretairy -p 5432:5432 postgres:16
docker run -d --name secretairy-redis -p 6379:6379 redis:7
docker run -d --name secretairy-qdrant -p 6333:6333 qdrant/qdrant
```

### 3. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Dashboard

```bash
cd dashboard
npm install
npm run dev
```

### 5. For Outbound Calls (Optional)

```bash
# Start a tunnel so Twilio can reach your server
cloudflared tunnel --url http://localhost:8000
# Copy the https URL to .env as TWILIO_WEBHOOK_BASE_URL
# Restart the backend
```

### 6. Verify

```bash
curl localhost:8000/health
# → {"status":"ok","checks":{"postgres":"ok","redis":"ok","qdrant":"ok"}}

# Open http://localhost:3000 in your browser
```

## Usage

### Step 1: Upload Your Resume
Go to the Profile page, paste your resume text, click "Upload & Analyze". Gemini extracts your skills, experience, and preferences.

### Step 2: Run Scout
Click "Run Scout" to ingest real job postings from Greenhouse (Anthropic, OpenAI, Vercel, etc.), Lever, and HN Who's Hiring.

### Step 3: View Matches
The AI scores every job against your profile (0-100). Browse ranked matches with AI-generated rationale explaining why each is a good fit.

### Step 4: Deep Research
On the Outreach → Ideas tab, click "Deep Research" on any match. SecretAIRY:
- Searches the web for company news, funding, leadership via Gemini
- Finds recruiters and hiring managers on LinkedIn via Exa
- Generates an enriched dossier with research-backed talking points

### Step 5: Outreach
Add discovered contacts, then create a campaign. SecretAIRY generates:
- **Call script** — opener, gatekeeper handling, pitch points, voicemail script
- **Email draft** — personalized cold email referencing specific research
- **LinkedIn message** — 300-char connection request

### Step 6: Make Calls
Click "Call Now" and SecretAIRY dials the contact via Twilio. The Gemini Live voice agent handles the conversation in real-time — introducing itself, pitching you, handling questions, and offering to schedule a callback.

### Autopilot Mode
Click "Run Autopilot" to execute the full pipeline automatically:
ingest → score → research top matches → discover contacts → generate outreach → queue calls

## API Reference

### Core

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | System health check |
| `POST` | `/profile/resume` | Upload and parse resume |
| `GET` | `/profile` | Get parsed profile |
| `POST` | `/ingest/run` | Scrape jobs from all sources |
| `GET` | `/opportunities` | List scraped jobs (paginated) |
| `POST` | `/matches/score` | Score all matches |
| `GET` | `/matches` | List ranked matches |

### Research & Outreach

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/research/{match_id}` | Deep research a company |
| `GET` | `/research/{match_id}` | Get research results |
| `POST` | `/autopilot/run` | Run full autopilot cycle |
| `GET` | `/autopilot/status` | Autopilot run status |

### Contacts & Campaigns

| Method | Path | Description |
|--------|------|-------------|
| `GET/POST` | `/contacts` | CRUD contacts |
| `GET/POST` | `/campaigns` | CRUD call campaigns |
| `POST` | `/campaigns/{id}/call-now` | Trigger outbound call |
| `POST` | `/campaigns/{id}/generate-script` | Generate call script |
| `GET` | `/campaigns/{id}/logs` | Call log history |

### Twilio Webhooks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/voice/outbound/twiml/{id}` | TwiML for Twilio |
| `WS` | `/voice/outbound/ws/{id}` | Media Stream WebSocket |
| `POST` | `/voice/outbound/status/{id}` | Call status callbacks |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.13, FastAPI, SQLAlchemy, Alembic |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS |
| **LLM** | Gemini 2.5 Flash (reasoning + Google Search grounding) |
| **Voice** | Pipecat + Gemini Live (native audio) + Twilio |
| **Embeddings** | Gemini `gemini-embedding-001` → Qdrant |
| **Search** | Exa API (structured web search for contacts) |
| **Scraping** | OpenClaw (browser automation for LinkedIn/career pages) |
| **Database** | PostgreSQL (data) + Redis (cache) + Qdrant (vectors) |
| **Tunneling** | Cloudflare Tunnel / ngrok (for Twilio webhooks) |

## Project Structure

```
SecretAIRY/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic
│   │   │   ├── research/     # Deep research engine
│   │   │   │   ├── engine.py         # Research orchestrator
│   │   │   │   ├── gemini_search.py  # Gemini + Google Search
│   │   │   │   ├── exa_search.py     # Exa contact discovery
│   │   │   │   └── openclaw_scrape.py # Browser scraping
│   │   │   ├── autopilot.py          # Full autopilot loop
│   │   │   ├── match_engine.py       # Job scoring engine
│   │   │   ├── outreach_gen.py       # Multi-channel generation
│   │   │   └── twilio_client.py      # Twilio REST API
│   │   └── voice/
│   │       └── outbound/     # Outbound calling pipeline
│   │           ├── server.py         # WebSocket + TwiML endpoints
│   │           ├── pipeline.py       # Pipecat voice pipeline
│   │           └── prompts.py        # Call script prompts
│   ├── alembic/              # Database migrations
│   └── tests/                # Test suite
├── dashboard/
│   ├── app/                  # Next.js pages
│   │   ├── page.tsx          # Profile upload
│   │   ├── jobs/             # Job database
│   │   ├── matches/          # Ranked matches
│   │   └── outreach/         # Multi-channel outreach hub
│   ├── components/           # React components
│   └── lib/                  # API client + types
├── .env.example
├── LICENSE (MIT)
└── README.md
```

## OpenClaw Integration

SecretAIRY supports [OpenClaw](https://github.com/openclaw) for deep browser-based scraping when API-based research isn't enough:

- **Career page scraping** — Extracts recruiter emails, phone numbers, and hiring team info from company career pages
- **LinkedIn profile enrichment** — Verifies contact names, titles, and public details
- **Company research** — Scrapes company pages for org charts and team information

Set `OPENCLAW_URL` in your `.env` to point to a running OpenClaw instance. SecretAIRY falls back to direct HTTP fetching if OpenClaw is unavailable.

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.
