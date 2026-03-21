# AGENTARY — The AI Research & Sales Agentic Platform

## From SecretAIRY to Agentary: The Full Pivot Blueprint

---

# TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [What We Have Today](#2-what-we-have-today)
3. [The Agentary Vision](#3-the-agentary-vision)
4. [What We Keep, Transform, and Build](#4-what-we-keep-transform-and-build)
5. [System Architecture](#5-system-architecture)
6. [Module Breakdown](#6-module-breakdown)
7. [Feature Universe](#7-feature-universe)
8. [Data Architecture](#8-data-architecture)
9. [Agent Orchestration Engine](#9-agent-orchestration-engine)
10. [Unique Differentiators](#10-unique-differentiators)
11. [Implementation Phases](#11-implementation-phases)
12. [Technical Specifications](#12-technical-specifications)

---

# 1. EXECUTIVE SUMMARY

**SecretAIRY** is a personal AI recruitment assistant — it finds jobs for YOU, researches companies, and makes outbound calls on YOUR behalf.

**Agentary** flips the script entirely. It becomes a **multi-tenant research and sales intelligence platform** where ANYONE can deploy autonomous AI agents that:
- Research ANY domain (not just jobs)
- Sell ANY product/service (not just yourself)
- Engage ANY audience (not just recruiters)
- Operate on ANY channel (voice, email, LinkedIn, SMS, WhatsApp, X/Twitter DMs)

Think of it as: **"Your AI sales team that never sleeps — researches, qualifies, reaches out, follows up, and books meetings while you focus on closing."**

### The Core Pivot

| Dimension | SecretAIRY (Now) | Agentary (Next) |
|-----------|-----------------|-----------------|
| **User** | Job seeker | Founder, SDR, agency, freelancer |
| **Target** | Companies hiring | Prospects buying |
| **Research** | Company intel for interviews | Prospect intel for sales |
| **Outreach** | Cold outreach for jobs | Cold outreach for deals |
| **Voice** | Call recruiters | Call prospects |
| **Pipeline** | Job application pipeline | Sales/deal pipeline |
| **Scoring** | Job-candidate fit | Lead-product fit |
| **Dossier** | Interview prep briefing | Sales call prep briefing |
| **Autopilot** | Auto-apply to jobs | Auto-prospect and engage |
| **Multi-tenant** | Single user | Teams, organizations |
| **Scale** | 1 person's job hunt | N users × M campaigns |

---

# 2. WHAT WE HAVE TODAY

### Reusable Infrastructure (Battle-Tested)
```
┌─────────────────────────────────────────────────────────────────┐
│                    SECRETAIRY CAPABILITY MAP                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  INGESTION    │  │   SCORING    │  │     RESEARCH          │  │
│  │              │  │              │  │                      │  │
│  │ • Greenhouse  │  │ • Hard filter│  │ • Gemini + Google    │  │
│  │ • Lever       │  │ • Semantic   │  │   Search grounding   │  │
│  │ • HN Who's    │  │   (Qdrant)   │  │ • Exa contact        │  │
│  │   Hiring      │  │ • LLM score  │  │   discovery          │  │
│  │ • Dedup       │  │ • Composite  │  │ • Fuzzy dedup        │  │
│  │ • Embed       │  │   weighting  │  │ • Quality scoring    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  OUTREACH     │  │    VOICE     │  │     AUTOMATION        │  │
│  │              │  │              │  │                      │  │
│  │ • Email       │  │ • Pipecat    │  │ • APScheduler cron   │  │
│  │   (Resend)    │  │ • Gemini Live│  │ • Autopilot cycle    │  │
│  │ • LinkedIn    │  │ • Twilio     │  │ • Background tasks   │  │
│  │   messages    │  │   Media      │  │ • Business hours     │  │
│  │ • Call        │  │   Streams    │  │   enforcement        │  │
│  │   scripts     │  │ • Transcript │  │ • Circuit breakers   │  │
│  │ • Sequences   │  │   capture    │  │ • Webhook tracking   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   PIPELINE    │  │  ANALYTICS   │  │      AUTH + DB        │  │
│  │              │  │              │  │                      │  │
│  │ • 8 stages    │  │ • Funnel     │  │ • JWT auth           │  │
│  │ • Transitions │  │ • Channel    │  │ • PostgreSQL         │  │
│  │ • Audit trail │  │   perf       │  │ • Redis              │  │
│  │ • Policy      │  │ • Timeline   │  │ • Qdrant             │  │
│  │   engine      │  │ • Score dist │  │ • Alembic migrations │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  FRONTEND: Next.js 14 + Tailwind + 14 routes + WebSocket Scout  │
│  INFRA: Docker Compose (5 services) + Nginx reverse proxy       │
└─────────────────────────────────────────────────────────────────┘
```

### Key Stats
- **15 database models** with full audit trail
- **12 API routers** with 50+ endpoints
- **17 service modules** with business logic
- **Real-time voice pipeline** (Pipecat + Gemini Live + Twilio)
- **Vector search** (Qdrant + Gemini embeddings, 3072 dims)
- **Multi-channel outreach** (email + LinkedIn + voice)
- **Automated pipeline** (ingest → score → research → outreach)

---

# 3. THE AGENTARY VISION

## What Is Agentary?

**Agentary is an AI-native sales and research platform where users deploy autonomous agent crews that prospect, research, qualify, and engage leads across every channel — culminating in AI voice calls that book meetings.**

### The Tagline Options
- *"Your AI sales team that never sleeps."*
- *"Deploy agents. Close deals."*
- *"Research → Qualify → Engage → Close. All on autopilot."*
- *"The agent platform for revenue teams."*

### Who Is It For?

| Persona | Use Case |
|---------|----------|
| **Indie Founders** | Outbound sales for their SaaS/product without hiring SDRs |
| **Freelancers/Consultants** | Finding and qualifying clients automatically |
| **Small Sales Teams** | Augmenting 2-3 person SDR teams with AI agents |
| **Agencies** | Managing outreach for multiple client campaigns |
| **Recruiters** | (Legacy SecretAIRY use case — still supported) |
| **Researchers** | Deep company/market/competitor research automation |
| **BD Teams** | Partnership prospecting and qualification |

### The 30-Second Pitch

> "You tell Agentary who your ideal customer is. It searches the internet for matching companies, finds the right people to talk to, researches everything about them, writes hyper-personalized emails and LinkedIn messages, and when you're ready — it calls them with an AI voice agent that sounds human, handles objections, and books meetings on your calendar. All while you sleep."

---

# 4. WHAT WE KEEP, TRANSFORM, AND BUILD

## 4.1 KEEP AS-IS (Core Infrastructure)
These modules are domain-agnostic and transfer directly:

| Module | Why It Transfers |
|--------|-----------------|
| `auth.py` + JWT | Auth is auth — works for any SaaS |
| `database.py` + SQLAlchemy | ORM layer is domain-agnostic |
| `circuit_breakers.py` | Fault tolerance for any external API |
| `gemini.py` (wrapper) | LLM client works for any use case |
| `qdrant_store.py` | Vector search works for any embeddings |
| `email_sender.py` | Email sending via Resend — universal |
| `twilio_client.py` | Voice calling infrastructure — universal |
| `scheduler.py` (APScheduler) | Cron scheduling — universal |
| `contact_dedup.py` | Fuzzy matching — universal |
| Docker Compose infra | PostgreSQL + Redis + Qdrant — universal |
| Nginx config | Reverse proxy — universal |
| Next.js dashboard shell | App shell, auth flow, nav — reusable |

## 4.2 TRANSFORM (Rename + Generalize)

| From (SecretAIRY) | To (Agentary) | What Changes |
|-------------------|---------------|-------------|
| `Profile` (resume) | `UserProfile` + `ProductProfile` | Users define their product/service, not their resume |
| `Opportunity` (job) | `Lead` / `Prospect` | Leads are companies/people to sell to, not jobs |
| `Match` (job fit) | `LeadScore` | Scoring is product-prospect fit, not job-candidate fit |
| `match_engine.py` | `lead_scorer.py` | Hard filters = ICP criteria, not role families |
| `Dossier` (interview prep) | `IntelBrief` | Briefing for sales calls, not interviews |
| `dossier_gen.py` | `intel_gen.py` | Generate sales intel, not interview prep |
| `CallCampaign` | `OutreachCampaign` | Broader: email sequences + calls + social |
| `outreach_gen.py` | `message_gen.py` | Generate for any persona/product combo |
| `research/engine.py` | `research/orchestrator.py` | Research any entity, not just hiring companies |
| `ingest/` connectors | `sources/` connectors | Pluggable source system for any data feed |
| `pipeline_engine.py` | `deal_pipeline.py` | Sales pipeline stages, not job pipeline |
| `autopilot.py` | `agent_loop.py` | Autonomous agent cycle for any workflow |
| `scout.py` (WebSocket) | `live_feed.py` | Real-time lead discovery stream |
| Voice prompts | Dynamic voice prompts | Persona-aware, product-aware call scripts |

## 4.3 BUILD NEW

These are entirely new capabilities:

| New Module | Purpose |
|-----------|---------|
| **Agent Builder** | Visual/config-driven agent creation |
| **ICP Engine** | Ideal Customer Profile definition + matching |
| **Multi-Campaign Manager** | Run N campaigns simultaneously |
| **Sequence Builder** | Drag-and-drop outreach sequences |
| **Intent Signal Detector** | Detect buying signals from web activity |
| **Competitive Intel** | Auto-track competitor moves |
| **Meeting Scheduler** | Cal.com/Calendly integration for booking |
| **CRM Sync** | Bidirectional sync with HubSpot/Salesforce/Pipedrive |
| **Team Workspace** | Multi-user orgs with roles/permissions |
| **Agent Marketplace** | Share/sell pre-built agent templates |
| **Conversation Intelligence** | Post-call analytics, coaching, insights |
| **A/B Testing Engine** | Test message variants automatically |
| **Enrichment Pipeline** | Waterfall enrichment from multiple data providers |
| **Webhook Builder** | Custom webhook integrations |
| **API Platform** | Public API for programmatic access |
| **Billing Engine** | Stripe integration, usage-based pricing |

---

# 5. SYSTEM ARCHITECTURE

## 5.1 High-Level Architecture

```
                            ┌─────────────────────────────┐
                            │      AGENTARY PLATFORM       │
                            └──────────────┬──────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
            ┌───────▼───────┐     ┌───────▼───────┐     ┌───────▼───────┐
            │   DASHBOARD    │     │   API LAYER    │     │  AGENT ENGINE  │
            │   (Next.js)    │     │   (FastAPI)    │     │   (Python)     │
            │               │     │               │     │               │
            │ • Campaign     │     │ • REST API    │     │ • Agent Loop   │
            │   Builder      │◄───►│ • WebSocket   │◄───►│ • Task Queue   │
            │ • Agent Studio │     │ • Webhooks    │     │ • Scheduler    │
            │ • Analytics    │     │ • Auth        │     │ • Orchestrator │
            │ • Live Feed    │     │ • Rate Limit  │     │ • State Mgmt   │
            └───────────────┘     └───────┬───────┘     └───────┬───────┘
                                          │                      │
                    ┌─────────────────────┼──────────────────────┤
                    │                     │                      │
            ┌───────▼───────┐    ┌───────▼───────┐     ┌───────▼───────┐
            │  DATA LAYER    │    │ INTELLIGENCE   │     │  COMMS LAYER   │
            │               │    │    LAYER        │     │               │
            │ • PostgreSQL   │    │               │     │ • Twilio       │
            │ • Redis        │    │ • Gemini LLM   │     │   (Voice)      │
            │ • Qdrant       │    │ • Embeddings   │     │ • Resend       │
            │ • S3/R2        │    │ • Research     │     │   (Email)      │
            │   (files)      │    │ • Scoring      │     │ • LinkedIn     │
            └───────────────┘    │ • Intent       │     │   (Social)     │
                                 │   Detection    │     │ • SMS          │
                                 └───────────────┘     │ • WhatsApp     │
                                                       └───────────────┘
```

## 5.2 Agent Execution Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AGENT EXECUTION ENGINE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  AGENT        │    │  TASK         │    │  STATE MACHINE       │  │
│  │  DEFINITION   │───►│  PLANNER      │───►│                      │  │
│  │              │    │              │    │  IDLE ──► RESEARCHING  │  │
│  │ • ICP rules   │    │ • Break into  │    │           │           │  │
│  │ • Persona     │    │   subtasks   │    │           ▼           │  │
│  │ • Channels    │    │ • Prioritize  │    │      QUALIFYING      │  │
│  │ • Limits      │    │ • Schedule    │    │           │           │  │
│  │ • Product     │    │ • Parallelize │    │           ▼           │  │
│  │   context     │    │              │    │      ENGAGING         │  │
│  └──────────────┘    └──────────────┘    │           │           │  │
│                                          │           ▼           │  │
│  ┌──────────────┐    ┌──────────────┐    │      FOLLOWING_UP     │  │
│  │  MEMORY       │    │  TOOLS        │    │           │           │  │
│  │  STORE        │    │  REGISTRY     │    │           ▼           │  │
│  │              │    │              │    │      MEETING_BOOKED   │  │
│  │ • Conv hist   │    │ • Web search  │    │           │           │  │
│  │ • Lead notes  │    │ • Email send  │    │           ▼           │  │
│  │ • Learnings   │    │ • Voice call  │    │      CLOSED_WON/LOST │  │
│  │ • Preferences │    │ • CRM update  │    │                      │  │
│  │ • Context     │    │ • Calendar    │    └──────────────────────┘  │
│  └──────────────┘    │ • Enrich      │                              │
│                      │ • LinkedIn    │                              │
│                      │ • SMS/WhatsApp│                              │
│                      └──────────────┘                              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    GUARDRAILS & SAFETY                       │    │
│  │                                                              │    │
│  │  • Rate limits per channel    • PII redaction               │    │
│  │  • Business hours only        • Compliance rules            │    │
│  │  • Daily budget caps          • Escalation triggers         │    │
│  │  • Suppression lists          • Human-in-the-loop gates     │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## 5.3 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AGENTARY DATA FLOW                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ═══════════════════ DISCOVERY PHASE ═══════════════════             │
│                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ LinkedIn  │   │ Crunchbase│   │ Product   │   │ Custom   │        │
│  │ Sales Nav │   │ / Apollo  │   │ Hunt      │   │ Scraper  │        │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘        │
│       │              │              │              │                │
│       └──────────────┴──────────────┴──────────────┘                │
│                              │                                      │
│                      ┌───────▼───────┐                              │
│                      │  LEAD POOL     │                              │
│                      │  (Raw leads)   │                              │
│                      └───────┬───────┘                              │
│                              │                                      │
│  ═══════════════════ ENRICHMENT PHASE ══════════════════            │
│                              │                                      │
│                      ┌───────▼───────┐                              │
│                      │  ENRICHMENT    │                              │
│                      │  WATERFALL     │                              │
│                      │              │                              │
│                      │ 1. Gemini     │                              │
│                      │    Search     │                              │
│                      │ 2. Exa API    │                              │
│                      │ 3. Apollo     │                              │
│                      │ 4. Clearbit   │                              │
│                      │ 5. Hunter.io  │                              │
│                      └───────┬───────┘                              │
│                              │                                      │
│  ═══════════════════ QUALIFICATION PHASE ═══════════════            │
│                              │                                      │
│                      ┌───────▼───────┐                              │
│                      │  ICP SCORER    │                              │
│                      │              │                              │
│                      │ • Firmographic │                              │
│                      │ • Technographic│                              │
│                      │ • Intent       │                              │
│                      │ • Behavioral   │                              │
│                      │ • Budget proxy │                              │
│                      └───────┬───────┘                              │
│                              │                                      │
│  ═══════════════════ ENGAGEMENT PHASE ══════════════════            │
│                              │                                      │
│              ┌───────────────┼───────────────┐                      │
│              │               │               │                      │
│       ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐               │
│       │   EMAIL      │ │  LINKEDIN   │ │   VOICE    │               │
│       │  Sequence    │ │  Outreach   │ │   Call     │               │
│       │             │ │            │ │           │               │
│       │ Day 1: Intro │ │ Connect    │ │ AI Agent   │               │
│       │ Day 3: Value │ │ request +  │ │ calls with │               │
│       │ Day 7: Case  │ │ follow-up  │ │ dynamic    │               │
│       │ Day 14: Last │ │ message    │ │ persona    │               │
│       └──────┬──────┘ └─────┬──────┘ └─────┬──────┘               │
│              │              │              │                        │
│              └──────────────┴──────────────┘                        │
│                             │                                       │
│  ═══════════════════ CONVERSION PHASE ══════════════════            │
│                             │                                       │
│                     ┌───────▼───────┐                               │
│                     │  MEETING       │                               │
│                     │  BOOKER        │                               │
│                     │               │                               │
│                     │ • Cal.com link │                               │
│                     │ • Calendly     │                               │
│                     │ • Direct       │                               │
│                     │   schedule     │                               │
│                     └───────┬───────┘                               │
│                             │                                       │
│                     ┌───────▼───────┐                               │
│                     │  DEAL          │                               │
│                     │  PIPELINE      │                               │
│                     │               │                               │
│                     │ Prospect       │                               │
│                     │ → Qualified    │                               │
│                     │ → Engaged      │                               │
│                     │ → Meeting Set  │                               │
│                     │ → Negotiation  │                               │
│                     │ → Closed Won   │                               │
│                     │ → Closed Lost  │                               │
│                     └───────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

## 5.4 Voice Agent Architecture (Enhanced)

```
┌─────────────────────────────────────────────────────────────────────┐
│                 AGENTARY VOICE AGENT SYSTEM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PRE-CALL                                                            │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  1. Pull lead intel (company, contact, research)          │       │
│  │  2. Pull product context (value props, pricing, USPs)     │       │
│  │  3. Generate dynamic system prompt with persona           │       │
│  │  4. Load objection handlers from knowledge base           │       │
│  │  5. Set conversation goals (book meeting, qualify, etc.)  │       │
│  │  6. Check policy (business hours, contact cooldown)       │       │
│  └──────────────────────────────────────────────────────────┘       │
│                              │                                       │
│  DURING CALL                  │                                       │
│  ┌──────────────────────────▼───────────────────────────────┐       │
│  │                                                           │       │
│  │  ┌─────────┐    ┌──────────┐    ┌─────────────────┐     │       │
│  │  │ Twilio   │◄──►│ Pipecat   │◄──►│ Gemini Live     │     │       │
│  │  │ Media    │    │ Pipeline  │    │ (Native Audio)  │     │       │
│  │  │ Stream   │    │          │    │                 │     │       │
│  │  │ 8kHz     │    │ VAD      │    │ • Persona voice │     │       │
│  │  │ μ-law    │    │ Denoise  │    │ • Real-time     │     │       │
│  │  └─────────┘    │ Transcript│    │   reasoning     │     │       │
│  │                  └──────────┘    │ • Tool calling  │     │       │
│  │                                  │   (calendar,    │     │       │
│  │                                  │    CRM, etc.)   │     │       │
│  │                                  └─────────────────┘     │       │
│  │                                                           │       │
│  │  ┌─────────────────────────────────────────────────┐     │       │
│  │  │  LIVE MONITORS                                   │     │       │
│  │  │  • Sentiment analysis (real-time)                │     │       │
│  │  │  • Objection detection + counter suggestion      │     │       │
│  │  │  • PII redaction in transcript                   │     │       │
│  │  │  • Compliance keyword flagging                   │     │       │
│  │  │  • Call duration limits                          │     │       │
│  │  │  • Human takeover trigger ("let me get my mgr")  │     │       │
│  │  └─────────────────────────────────────────────────┘     │       │
│  └──────────────────────────────────────────────────────────┘       │
│                              │                                       │
│  POST-CALL                   │                                       │
│  ┌──────────────────────────▼───────────────────────────────┐       │
│  │  1. AI classifies outcome (connected, voicemail, etc.)    │       │
│  │  2. Extract action items from transcript                  │       │
│  │  3. Update CRM / deal pipeline automatically              │       │
│  │  4. Schedule follow-up actions (email, callback)          │       │
│  │  5. Generate call summary for user review                 │       │
│  │  6. Feed learnings back to agent memory                   │       │
│  │  7. Score call quality (0-100)                            │       │
│  │  8. Update contact engagement timeline                    │       │
│  └──────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

---

# 6. MODULE BREAKDOWN

## 6.1 Core Platform Modules

### Module 1: AGENT BUILDER
**Purpose:** Let users create, configure, and deploy autonomous agents without code.

```
agent_builder/
├── agent_definition.py       # Agent config schema (ICP, persona, channels, limits)
├── persona_engine.py         # Define agent personality, tone, knowledge
├── icp_builder.py            # Define ideal customer profile rules
├── channel_config.py         # Configure which channels agent uses
├── knowledge_base.py         # Upload product docs, FAQs, objection handlers
├── constraint_engine.py      # Set limits (calls/day, emails/day, budget)
└── template_library.py       # Pre-built agent templates
```

**Key Concepts:**
- An "Agent" is a configured autonomous workflow
- Each agent has: ICP rules, persona, channels, knowledge, constraints
- Agents can be cloned, shared, versioned
- Templates for common use cases (SaaS SDR, recruiter, consultant, etc.)

---

### Module 2: LEAD DISCOVERY ENGINE
**Purpose:** Find prospects matching the ICP from multiple sources.

```
discovery/
├── orchestrator.py           # Coordinate multi-source discovery
├── sources/
│   ├── linkedin_source.py    # LinkedIn Sales Nav / scraping
│   ├── crunchbase_source.py  # Company database
│   ├── producthunt_source.py # Newly launched companies
│   ├── github_source.py      # Open source project maintainers
│   ├── twitter_source.py     # Twitter/X bio + engagement analysis
│   ├── hn_source.py          # Hacker News (keep existing)
│   ├── greenhouse_source.py  # Companies hiring (signals growth)
│   ├── lever_source.py       # Companies hiring (keep existing)
│   ├── job_board_source.py   # Generic job board connector
│   ├── g2_source.py          # G2 reviews (competitor users)
│   ├── reddit_source.py      # Reddit discussions / pain points
│   ├── custom_csv_source.py  # Import CSV lead lists
│   ├── webhook_source.py     # Receive leads via webhook
│   └── api_source.py         # Connect any API as source
├── dedup_engine.py           # Cross-source deduplication
└── lead_pool.py              # Unified lead storage
```

**Unique Sources & Signals:**
- **Job postings as intent signals** — company hiring SDRs = growing sales team = might need tools
- **GitHub stars/contributions** — find CTOs who use specific tech stacks
- **Product Hunt launches** — newly funded startups that need everything
- **G2 reviews** — people reviewing competitor products = warm prospects
- **Reddit pain threads** — people complaining about problems you solve

---

### Module 3: ENRICHMENT PIPELINE
**Purpose:** Fill in missing data about leads using a waterfall of providers.

```
enrichment/
├── waterfall.py              # Try providers in order until data found
├── providers/
│   ├── gemini_enricher.py    # Google Search grounding (keep existing)
│   ├── exa_enricher.py       # Exa contact discovery (keep existing)
│   ├── apollo_enricher.py    # Apollo.io for email/phone
│   ├── clearbit_enricher.py  # Company firmographics
│   ├── hunter_enricher.py    # Email finder
│   ├── zoominfo_enricher.py  # Enterprise contact data
│   ├── builtwith_enricher.py # Technographic data
│   ├── similarweb_enricher.py# Web traffic data
│   └── scraper_enricher.py   # Custom web scraping fallback
├── field_resolver.py         # Smart field-level resolution
└── quality_scorer.py         # Rate enrichment completeness
```

**Waterfall Logic:**
```
For each missing field:
  1. Try cheapest provider first
  2. If not found → try next provider
  3. If still not found → try AI extraction from web
  4. If still not found → mark as "needs manual input"
  5. Cache all results to avoid re-querying
```

---

### Module 4: ICP SCORING ENGINE
**Purpose:** Score leads against the user's Ideal Customer Profile.

```
scoring/
├── icp_scorer.py             # Main scoring orchestrator
├── dimensions/
│   ├── firmographic.py       # Company size, revenue, industry, location
│   ├── technographic.py      # Tech stack, tools used, integrations
│   ├── intent.py             # Buying signals (hiring, funding, tech changes)
│   ├── behavioral.py         # Website visits, content engagement, social activity
│   ├── budget.py             # Revenue proxy, funding, employee count → budget estimate
│   ├── timing.py             # Fiscal year, budget cycle, contract renewal signals
│   └── fit.py                # LLM-based holistic fit analysis with rationale
├── weights.py                # User-configurable scoring weights
├── thresholds.py             # Auto-qualify / auto-disqualify rules
└── feedback_loop.py          # Learn from won/lost deals to improve scoring
```

**Scoring Dimensions (0-100 each, weighted composite):**
```
┌────────────────────────────────────────────────┐
│            ICP SCORE COMPOSITION                │
│                                                 │
│  Firmographic Score   ████████░░  35%           │
│  (size, industry, geo)                          │
│                                                 │
│  Technographic Score  ██████░░░░  20%           │
│  (tech stack match)                             │
│                                                 │
│  Intent Score         ████░░░░░░  15%           │
│  (buying signals)                               │
│                                                 │
│  Behavioral Score     ███░░░░░░░  10%           │
│  (engagement level)                             │
│                                                 │
│  Budget Proxy         ████░░░░░░  10%           │
│  (can they afford it?)                          │
│                                                 │
│  LLM Fit Analysis     ██░░░░░░░░  10%           │
│  (holistic reasoning)                           │
│                                                 │
│  ═══════════════════════════════                │
│  COMPOSITE SCORE: 73/100        ★ QUALIFIED     │
└────────────────────────────────────────────────┘
```

---

### Module 5: MULTI-CHANNEL OUTREACH ENGINE
**Purpose:** Execute coordinated outreach across email, LinkedIn, voice, SMS, and more.

```
outreach/
├── sequence_builder.py       # Define multi-step outreach sequences
├── sequence_executor.py      # Execute sequences with timing
├── channels/
│   ├── email_channel.py      # Email via Resend (keep existing)
│   ├── linkedin_channel.py   # LinkedIn connect + message
│   ├── voice_channel.py      # AI voice calls via Twilio (keep existing)
│   ├── sms_channel.py        # SMS via Twilio
│   ├── whatsapp_channel.py   # WhatsApp Business API
│   ├── twitter_channel.py    # Twitter/X DMs
│   └── slack_channel.py      # Slack Connect messages
├── message_gen.py            # AI message generation (keep + enhance existing)
├── personalization.py        # Deep personalization from research data
├── ab_testing.py             # A/B test message variants
├── send_time_optimizer.py    # ML-based optimal send time prediction
├── reply_detector.py         # Detect and classify replies
├── thread_manager.py         # Manage conversation threads
└── unsubscribe_handler.py    # CAN-SPAM / GDPR compliance
```

**Sequence Example:**
```
Day 0:  📧 Personalized intro email (research-powered)
Day 1:  🔗 LinkedIn connection request + note
Day 3:  📧 Value-add follow-up (case study / insight)
Day 3:  🔗 LinkedIn: engage with their recent post
Day 7:  📧 Social proof email (testimonial / metric)
Day 10: 📞 AI voice call (if email opened but no reply)
Day 14: 📧 Break-up email ("not the right time?")
Day 14: 🔗 LinkedIn follow-up message
```

---

### Module 6: CONVERSATION INTELLIGENCE
**Purpose:** Analyze all interactions (calls, emails, chats) for insights and coaching.

```
conversation_intel/
├── call_analyzer.py          # Post-call transcript analysis
├── email_analyzer.py         # Email thread analysis
├── sentiment_tracker.py      # Track sentiment across interactions
├── objection_detector.py     # Identify and categorize objections
├── buying_signal_detector.py # Detect positive purchase signals
├── talk_ratio_analyzer.py    # Agent vs prospect talk time
├── question_extractor.py     # Extract questions asked by prospect
├── action_item_extractor.py  # Extract commitments and next steps
├── coaching_engine.py        # Generate coaching suggestions
├── win_loss_analyzer.py      # Analyze patterns in won vs lost deals
└── keyword_tracker.py        # Track competitor mentions, pricing talk
```

---

### Module 7: DEAL PIPELINE & CRM
**Purpose:** Track deals from prospect to close with full audit trail.

```
pipeline/
├── deal_pipeline.py          # Pipeline stage management (transform existing)
├── stage_automation.py       # Auto-advance stages based on events
├── kanban_view.py            # API for Kanban board data
├── deal_value_estimator.py   # Estimate deal value from signals
├── forecast_engine.py        # Pipeline forecasting
├── activity_timeline.py      # Full interaction timeline per lead
├── crm_sync/
│   ├── hubspot.py            # Bidirectional HubSpot sync
│   ├── salesforce.py         # Bidirectional Salesforce sync
│   ├── pipedrive.py          # Bidirectional Pipedrive sync
│   └── sync_engine.py        # Conflict resolution, field mapping
└── reports/
    ├── pipeline_report.py    # Pipeline health metrics
    ├── activity_report.py    # Team activity metrics
    ├── conversion_report.py  # Stage-to-stage conversion rates
    └── revenue_report.py     # Revenue attribution
```

---

### Module 8: MEETING SCHEDULER
**Purpose:** Book meetings automatically from voice calls and email replies.

```
scheduling/
├── calendar_connector.py     # Connect to Google Calendar, Outlook, Cal.com
├── availability_engine.py    # Check real-time availability
├── booking_engine.py         # Create calendar events
├── timezone_resolver.py      # Handle timezone complexity
├── reminder_engine.py        # Send meeting reminders
├── reschedule_handler.py     # Handle reschedule requests
├── noshow_handler.py         # Follow up on no-shows
└── meeting_prep.py           # Auto-generate meeting prep docs
```

---

### Module 9: ANALYTICS & INSIGHTS ENGINE
**Purpose:** Deep analytics on every aspect of the sales process.

```
analytics/
├── funnel_analytics.py       # Pipeline funnel (transform existing)
├── channel_analytics.py      # Per-channel performance (transform existing)
├── agent_analytics.py        # Per-agent performance metrics
├── campaign_analytics.py     # Per-campaign ROI
├── ab_test_analytics.py      # A/B test results and significance
├── time_series.py            # Activity over time (transform existing)
├── cohort_analysis.py        # Lead cohort behavior
├── attribution_engine.py     # Multi-touch attribution
├── benchmark_engine.py       # Compare against industry benchmarks
├── anomaly_detector.py       # Alert on unusual patterns
├── predictive/
│   ├── lead_score_predictor.py    # Predict which leads will convert
│   ├── churn_predictor.py         # Predict deal churn risk
│   ├── best_time_predictor.py     # Predict best contact times
│   └── revenue_forecaster.py      # Revenue prediction
└── dashboards/
    ├── executive_dashboard.py     # High-level KPIs
    ├── agent_dashboard.py         # Individual agent metrics
    └── campaign_dashboard.py      # Campaign drill-down
```

---

### Module 10: TEAM & ORGANIZATION
**Purpose:** Multi-user workspaces with roles, permissions, and collaboration.

```
teams/
├── organization.py           # Org model (name, plan, billing)
├── team.py                   # Team within org
├── membership.py             # User membership + roles
├── roles.py                  # Role definitions (admin, manager, member, viewer)
├── permissions.py            # Granular permission checks
├── invitation.py             # Invite flow (email + link)
├── audit_log.py              # Who did what when
└── usage_tracker.py          # Per-org usage metering (for billing)
```

---

## 6.2 Dashboard Pages (New)

```
AGENTARY DASHBOARD SITEMAP
═══════════════════════════

/                           → Command Center (overview dashboard)
/login                      → Auth (keep existing)
/onboarding                 → NEW: Guided setup wizard
/agents                     → NEW: Agent list + creation
/agents/[id]                → NEW: Agent detail + config
/agents/[id]/builder        → NEW: Visual agent builder
/campaigns                  → Campaign list (transform outreach)
/campaigns/[id]             → Campaign detail + analytics
/campaigns/[id]/sequences   → NEW: Sequence builder
/leads                      → Lead database (transform opportunities)
/leads/[id]                 → Lead detail + timeline
/pipeline                   → NEW: Kanban deal pipeline
/research                   → NEW: Research hub
/research/[id]              → NEW: Intel brief detail
/contacts                   → Contact management (keep existing)
/contacts/[id]              → Contact detail + history
/calls                      → Call center (transform existing)
/calls/[id]                 → Call detail + transcript
/analytics                  → Analytics hub (transform existing)
/analytics/agents           → NEW: Agent performance
/analytics/campaigns        → NEW: Campaign ROI
/analytics/calls            → NEW: Call analytics
/settings                   → NEW: Account settings
/settings/integrations      → NEW: CRM, calendar, etc.
/settings/billing           → NEW: Subscription management
/settings/team              → NEW: Team management
/marketplace                → NEW: Agent template marketplace
/live                       → Live feed (transform scout)
```

---

# 7. FEATURE UNIVERSE

## 7.1 CORE FEATURES (Must-Have for MVP)

### F1: Product/Service Profile Builder
Instead of uploading a resume, users describe their product/service:
- What they sell (product name, category, pricing)
- Value propositions (why someone should buy)
- Target customer description (ICP in natural language)
- Competitive advantages
- Case studies / social proof
- Objection handlers
- AI extracts structured ICP rules from natural language descriptions

### F2: ICP-Based Lead Discovery
- Define ICP criteria (industry, company size, tech stack, funding stage, etc.)
- Search across 10+ data sources simultaneously
- Real-time streaming results (like existing Scout, but for leads)
- Save and reuse ICP definitions
- Auto-discover new leads matching ICP on a schedule

### F3: Lead Enrichment Waterfall
- Automatically enrich every discovered lead
- Waterfall through multiple data providers
- Find email, phone, LinkedIn, company details, tech stack
- Quality score for each lead (how complete is the data?)
- Manual enrichment fallback queue

### F4: AI Message Generation (Per-Channel)
- Generate hyper-personalized messages using lead research
- Support all channels: email, LinkedIn, SMS, voice scripts
- Enforce channel constraints (LinkedIn: 300 chars, email: 150-250 words)
- Reference specific details from research (recent funding, job postings, etc.)
- A/B variant generation (generate 3 versions, test which performs best)

### F5: Multi-Step Sequence Builder
- Drag-and-drop sequence editor
- Mix channels (email → LinkedIn → call → email)
- Configurable delays between steps
- Conditional branching (if opened → do X, if replied → do Y)
- Auto-pause on reply
- Templates for common sequences

### F6: AI Voice Calling
- Autonomous outbound calls with natural conversation (keep existing Pipecat + Gemini Live)
- Dynamic persona based on product and prospect
- Real-time objection handling from knowledge base
- Goal-oriented: qualify, book meeting, gather info
- Live transcript streaming
- Post-call AI classification and follow-up scheduling

### F7: Deal Pipeline
- Kanban board with drag-and-drop stages
- Auto-advance based on engagement events
- Deal value tracking
- Stage duration analytics
- Win/loss tracking with reasons

### F8: Analytics Dashboard
- Pipeline funnel visualization
- Channel performance comparison
- Agent performance leaderboard
- Campaign ROI tracking
- Activity timeline
- Reply rate, open rate, connect rate metrics

---

## 7.2 ADVANCED FEATURES (Differentiators)

### F9: Intent Signal Detection
**Unique.** Monitor the web for buying signals from target accounts:
- Job postings (hiring for roles related to your product = need your tool)
- Funding announcements (just raised = have budget)
- Technology changes (adopted competitor = evaluate alternatives)
- Leadership changes (new CTO/VP = new tool decisions)
- Content engagement (reading articles about problems you solve)
- G2/Capterra review activity (researching your category)

```
INTENT SIGNAL TYPES
═══════════════════

🔥 HOT SIGNALS (Score boost: +30)
  • Searching for your product category on G2
  • Requesting demos from competitors
  • Job posting mentions your tool category

🟡 WARM SIGNALS (Score boost: +15)
  • Recently raised funding (Series A/B/C)
  • Hired new CTO/VP Engineering
  • Expanding team (10+ job postings)
  • Tech stack change detected

🟢 COOL SIGNALS (Score boost: +5)
  • Published content about relevant problems
  • Engaged with industry thought leaders
  • Attending relevant conferences
```

### F10: Competitive Intelligence Agent
**Unique.** Autonomous agent that tracks your competitors:
- Monitor competitor pricing page changes
- Track competitor G2/Capterra reviews
- Alert on competitor funding/hiring/product launches
- Identify competitor customers (from case studies, reviews, job posts)
- Generate "switch from [competitor]" talk tracks
- Auto-update your agents with competitive intel

### F11: Ghost Writer Mode
**Unique.** AI that writes content that generates inbound leads:
- Analyze what prospects are discussing on LinkedIn/Twitter/Reddit
- Generate thought leadership posts for the user to publish
- Write comments on prospect posts (warm them up before outreach)
- Create micro-case studies from won deals
- Generate content that addresses common objections
- Track which content drives the most responses

### F12: Warm Introduction Finder
**Unique.** Find mutual connections who can introduce you:
- Analyze user's LinkedIn network
- Cross-reference with target contacts
- Identify 2nd-degree connections at target companies
- Generate introduction request templates
- Track introduction requests and follow-ups

### F13: Deal Room
**Unique.** Shared digital sales room for each prospect:
- Auto-generated from research and interactions
- Contains: company intel, relevant case studies, pricing, timeline
- Share link with prospect
- Track prospect engagement (which pages viewed, time spent)
- Auto-notify agent when prospect views content
- Collect e-signatures for proposals

### F14: Objection Library + Training
**Unique.** Crowdsourced objection handling:
- Automatically extract objections from call transcripts
- Categorize (price, timing, competition, authority, need)
- Record which responses work best
- Train voice agent on successful responses
- Share objection handlers across team

### F15: Revenue Intelligence
**Unique.** Predict revenue from pipeline:
- Deal velocity tracking (days in each stage)
- Win probability estimation per deal
- Revenue forecast (weekly/monthly/quarterly)
- Risk alerts (deals stuck, going dark, unlikely to close)
- Coaching suggestions based on winning patterns

### F16: Multi-Persona Voice Agents
**Unique.** Different AI voices for different scenarios:
- SDR persona (energetic, discovery-focused)
- Account Executive persona (consultative, solution-focused)
- Customer Success persona (warm, relationship-focused)
- Technical persona (deep-dive, spec-focused)
- Each persona has different voice, tone, vocabulary, approach

### F17: Call Coaching Sidekick
**Unique.** Real-time coaching during live calls:
- If agent detects buying signal → flash suggestion card
- If prospect raises objection → show best response
- If agent talks too much → nudge to ask question
- If prospect asks pricing → show pricing guidance
- Post-call coaching report with specific improvements

### F18: Smart Follow-Up Engine
**Unique.** AI decides the best follow-up action:
- Analyze all past interactions with the contact
- Consider: channel used, message sent, response received, time elapsed
- Decide: what channel, what message, when to send
- Learn from what works for similar prospects
- Handle complex scenarios: "They replied asking to contact them next quarter"

---

## 7.3 INTEGRATION FEATURES

### F19: CRM Bidirectional Sync
- HubSpot, Salesforce, Pipedrive, Close.com
- Sync leads, contacts, deals, activities
- Conflict resolution (which system wins?)
- Field mapping configuration
- Real-time sync via webhooks

### F20: Calendar Integration
- Google Calendar, Outlook, Cal.com, Calendly
- Real-time availability checking
- Auto-book meetings from voice calls
- Meeting prep doc generation
- Post-meeting follow-up automation

### F21: Slack/Teams Notifications
- Deal alerts in team channels
- Daily/weekly summary bots
- Quick actions from Slack (approve outreach, advance stage)
- Live call notifications

### F22: Zapier/Make Webhooks
- Custom webhook endpoints for any automation
- Trigger Agentary actions from external events
- Send Agentary events to external tools

### F23: Data Import/Export
- CSV import for lead lists
- CSV export for any data
- API for programmatic access
- Bulk operations support

---

## 7.4 PLATFORM FEATURES

### F24: Agent Marketplace
**Unique.** Share and discover agent templates:
- Pre-configured agents for common use cases
- Community-contributed templates
- Rating and review system
- One-click deploy
- Revenue sharing for template creators

### F25: Usage-Based Billing
- Stripe integration
- Plans: Free, Pro, Business, Enterprise
- Metered: calls, emails, enrichments, AI credits
- Per-seat pricing for teams
- Usage dashboards and alerts

### F26: Onboarding Wizard
- Guided setup in 5 steps:
  1. Describe your product/service
  2. Define your ideal customer
  3. Connect your email/phone
  4. Import existing contacts (optional)
  5. Launch your first agent

### F27: White-Label Mode
- Agencies can white-label Agentary for their clients
- Custom domain, logo, colors
- Client-facing dashboards
- Agency management portal

### F28: Compliance Engine
- CAN-SPAM compliance for emails
- TCPA compliance for calls
- GDPR compliance for EU contacts
- Opt-out / unsubscribe handling
- Do-not-call list integration
- Consent management

---

## 7.5 WILD IDEAS (Moonshots)

### F29: Autonomous Negotiator
AI agent that can negotiate pricing and terms:
- User sets acceptable ranges (price, payment terms, contract length)
- Agent negotiates within those bounds during calls
- Handles common negotiation tactics
- Escalates to human when outside bounds

### F30: Voice Cloning
Let users clone their own voice for AI calls:
- Record 30 seconds of speech
- Generate voice model
- AI calls sound like the actual user
- Ethical guardrails (disclosure that it's AI where legally required)

### F31: Video Prospecting Agent
AI generates personalized video messages:
- Use AI avatar that looks natural
- Reference prospect's company/role specifically
- Embed in emails for higher response rates
- Track video view analytics

### F32: Social Listening Radar
Monitor social media for buying opportunities:
- "We're looking for a [your category]" posts
- "Frustrated with [competitor]" complaints
- "Anyone recommend a [your solution type]?" requests
- Auto-engage with relevant comment + follow up

### F33: Predictive Lead Scoring (ML)
Train a custom ML model on your closed deals:
- Feed in won deals + lost deals
- Model learns your unique winning patterns
- Predict which new leads will convert
- Continuously improve with new data

### F34: Agent-to-Agent Marketplace
Unique concept: Agents from different users can interact:
- Your sales agent finds someone else's procurement agent
- They negotiate and exchange information autonomously
- Humans get notified only when there's a match
- Think "Tinder for B2B sales"

### F35: Context-Aware Time Zone Intelligence
Smart outreach timing based on:
- Prospect's actual timezone (not just company HQ)
- Their typical active hours (from email response patterns)
- Industry norms (finance = early morning, tech = mid-morning)
- Day-of-week patterns (Tuesday-Thursday best for cold outreach)

### F36: Deal Risk Alerts
AI monitors deals and flags risks:
- "This deal has been in 'Negotiation' for 14 days — typical close is 5 days"
- "Prospect opened proposal 3 times but hasn't responded — send follow-up?"
- "Competitor mentioned in last call — prepare battle card"
- "Decision maker changed roles — research new contact"

### F37: Auto-Generated Battle Cards
For each competitor detected in conversations:
- Pull latest competitor info (pricing, features, reviews)
- Generate side-by-side comparison
- Include winning talk tracks from past deals
- Auto-update when competitor makes changes

### F38: Prospect Activity Feed
Real-time feed of all prospect interactions:
- Email opens/clicks
- Website visits (with Agentary pixel)
- LinkedIn profile views
- Call outcomes
- Content downloads
- Meeting attendances

### F39: Multi-Language Outreach
AI agents that speak multiple languages:
- Detect prospect's preferred language
- Generate outreach in their language
- Voice calls in their language
- Translate responses back for the user

### F40: Referral Chain Mapping
Map how deals flow through referral networks:
- Track which contacts refer other contacts
- Identify super-connectors
- Optimize referral incentive programs
- Visualize network effects

### F41: Smart Cadence Adaptation
AI adjusts outreach cadence based on engagement:
- High engagement → accelerate (contact sooner)
- Low engagement → decelerate (space out more)
- Negative signals → pause and try different angle
- Positive signals → prioritize for voice call

### F42: Revenue Attribution Waterfall
Track exactly which touchpoints led to revenue:
- First touch attribution
- Last touch attribution
- Multi-touch weighted attribution
- Compare channel effectiveness by revenue generated

### F43: AI Email Warm-Up
Before launching cold email campaigns:
- Gradually warm up email domains
- Build sender reputation
- Monitor deliverability scores
- Alert on blacklist risks
- Auto-rotate sending domains

### F44: Dynamic Pricing Intelligence
If selling services with flexible pricing:
- Research prospect's budget signals
- Adjust pricing in proposals
- Track price sensitivity across segments
- Optimize pricing based on close rates

### F45: Account-Based Marketing (ABM) Mode
Coordinate multi-contact outreach within a single company:
- Target multiple stakeholders simultaneously
- Coordinate messaging across contacts
- Track account-level engagement score
- Identify buying committee members
- Role-specific messaging (CTO gets tech pitch, CFO gets ROI pitch)

---

# 8. DATA ARCHITECTURE

## 8.1 New Schema (Extending Existing)

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENTARY DATA MODEL                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ORGANIZATION LAYER                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Organization │───►│    Team       │───►│   Member     │       │
│  │             │    │              │    │              │       │
│  │ • name      │    │ • name       │    │ • user_id    │       │
│  │ • plan      │    │ • org_id     │    │ • team_id    │       │
│  │ • billing   │    │              │    │ • role       │       │
│  └─────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
│  AGENT LAYER                                                     │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Agent      │───►│  AgentRun     │───►│  AgentTask   │       │
│  │             │    │              │    │              │       │
│  │ • name      │    │ • agent_id   │    │ • run_id     │       │
│  │ • icp_rules │    │ • started_at │    │ • type       │       │
│  │ • persona   │    │ • status     │    │ • status     │       │
│  │ • channels  │    │ • results    │    │ • result     │       │
│  │ • knowledge │    │              │    │              │       │
│  │ • limits    │    └──────────────┘    └──────────────┘       │
│  └─────────────┘                                                │
│                                                                  │
│  LEAD LAYER                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │    Lead      │───►│  LeadScore   │    │  LeadSignal  │       │
│  │             │    │              │    │              │       │
│  │ • company   │    │ • lead_id    │    │ • lead_id    │       │
│  │ • industry  │    │ • agent_id   │    │ • type       │       │
│  │ • size      │    │ • firmograph │    │ • source     │       │
│  │ • source    │    │ • technograph│    │ • strength   │       │
│  │ • enriched  │    │ • intent     │    │ • raw_data   │       │
│  │   _data     │    │ • composite  │    │              │       │
│  └──────┬──────┘    └──────────────┘    └──────────────┘       │
│         │                                                        │
│         │  ┌──────────────┐                                      │
│         └─►│   Contact     │ (keep existing, add fields)         │
│            │              │                                      │
│            │ • lead_id    │                                      │
│            │ • role_type  │  (decision_maker, influencer,        │
│            │              │   champion, blocker, user)            │
│            │ • engagement │                                      │
│            │   _score     │                                      │
│            └──────────────┘                                      │
│                                                                  │
│  OUTREACH LAYER                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Sequence    │───►│ SequenceStep │───►│  StepExec    │       │
│  │             │    │              │    │              │       │
│  │ • name      │    │ • channel    │    │ • step_id    │       │
│  │ • steps     │    │ • delay_days │    │ • contact_id │       │
│  │ • ab_test   │    │ • template   │    │ • sent_at    │       │
│  │             │    │ • conditions │    │ • response   │       │
│  └─────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
│  DEAL LAYER                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │    Deal      │───►│  Activity    │    │  DealNote    │       │
│  │             │    │              │    │              │       │
│  │ • lead_id   │    │ • deal_id    │    │ • deal_id    │       │
│  │ • stage     │    │ • type       │    │ • content    │       │
│  │ • value     │    │ • channel    │    │ • author     │       │
│  │ • close_date│    │ • outcome    │    │              │       │
│  │ • probability│   │ • metadata   │    │              │       │
│  └─────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
│  INTELLIGENCE LAYER (keep existing, rename + extend)             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  IntelBrief  │    │  Research     │    │ CallRecord   │       │
│  │ (ex-Dossier) │    │  Result       │    │ (ex-CallLog) │       │
│  │             │    │ (keep)        │    │              │       │
│  │ • lead_id   │    │ • lead_id    │    │ • transcript │       │
│  │ • content   │    │ • intel      │    │ • sentiment  │       │
│  │ • sections  │    │ • contacts   │    │ • coaching   │       │
│  │ • use_case  │    │ • quality    │    │ • next_steps │       │
│  │   (sales/   │    │              │    │              │       │
│  │    research) │    │              │    │              │       │
│  └─────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
│  KEEP FROM SECRETAIRY (rename where noted):                      │
│  • User → keep                                                   │
│  • Profile → ProductProfile (what you sell, not who you are)     │
│  • EmailEvent → keep                                             │
│  • EmailSuppression → keep                                       │
│  • Policy → keep (expand rules)                                  │
│  • PipelineTransition → DealTransition                           │
│  • ActionLog → AuditLog (expand scope)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

# 9. AGENT ORCHESTRATION ENGINE

## 9.1 Agent Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                  AGENT LIFECYCLE                             │
│                                                              │
│  CREATE          CONFIGURE        DEPLOY          MONITOR    │
│  ┌─────┐        ┌─────────┐      ┌──────┐       ┌────────┐ │
│  │ New  │───────►│ ICP     │─────►│ Live │──────►│ Metrics│ │
│  │Agent │       │ Persona │      │      │       │ Alerts │ │
│  └─────┘       │ Channels│      │      │       │ Logs   │ │
│                │ Knowledge│      │      │       │        │ │
│                │ Limits   │      │      │       │        │ │
│                └─────────┘      └──┬───┘       └────────┘ │
│                                    │                       │
│                              ┌─────▼─────┐                │
│                              │  AGENT     │                │
│                              │  RUN LOOP  │                │
│                              │           │                │
│                              │ 1. Discover│                │
│                              │ 2. Enrich  │                │
│                              │ 3. Score   │                │
│                              │ 4. Research│                │
│                              │ 5. Engage  │                │
│                              │ 6. Follow  │                │
│                              │    up      │                │
│                              │ 7. Report  │                │
│                              └───────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## 9.2 Agent Run Loop (Detailed)

```
AGENT RUN LOOP (every N hours, configurable)
═══════════════════════════════════════════

Step 1: DISCOVER
  ├─ Query all configured sources for new leads matching ICP
  ├─ Deduplicate against existing lead pool
  ├─ Store new leads with source attribution
  └─ Emit: "X new leads discovered from Y sources"

Step 2: ENRICH
  ├─ For each new lead, run enrichment waterfall
  ├─ Find: email, phone, LinkedIn, company data, tech stack
  ├─ Score enrichment quality (0-100)
  └─ Emit: "X leads enriched, avg quality: Y%"

Step 3: SCORE
  ├─ Score each enriched lead against ICP rules
  ├─ Apply all scoring dimensions (firmographic, technographic, intent, etc.)
  ├─ Auto-qualify leads above threshold
  ├─ Auto-disqualify leads below threshold
  └─ Emit: "X leads qualified (avg score: Y), Z disqualified"

Step 4: RESEARCH
  ├─ For top N qualified leads, run deep research
  ├─ Gemini Search + Exa + Apollo (parallel)
  ├─ Generate Intel Brief (sales prep, not interview prep)
  ├─ Auto-discover decision makers at company
  └─ Emit: "X leads researched, Y contacts discovered"

Step 5: ENGAGE
  ├─ For researched leads with contacts, create outreach campaign
  ├─ Generate personalized messages for each channel
  ├─ Enroll contacts in configured sequence
  ├─ Execute first step (usually email)
  └─ Emit: "X contacts enrolled in sequences, Y first touches sent"

Step 6: FOLLOW UP
  ├─ Process sequence steps that are due
  ├─ Check for replies and engagement signals
  ├─ Auto-pause sequences on reply
  ├─ Advance deals based on engagement
  ├─ Schedule voice calls for high-engagement leads
  └─ Emit: "X follow-ups sent, Y replies detected, Z calls scheduled"

Step 7: REPORT
  ├─ Compile run summary
  ├─ Update agent metrics
  ├─ Send notification to user (Slack, email, dashboard)
  └─ Emit: "Agent run complete. Summary: ..."
```

## 9.3 Agent Configuration Schema

```json
{
  "agent": {
    "name": "SaaS Sales Agent",
    "description": "Finds and engages SaaS decision makers",
    "schedule": "0 9 * * 1-5",
    "timezone": "America/New_York",
    "business_hours_only": true,

    "product_profile": {
      "name": "Agentary",
      "category": "AI Sales Platform",
      "pricing": "$99/mo - $999/mo",
      "value_props": [
        "Autonomous AI agents that prospect and sell",
        "Multi-channel outreach on autopilot",
        "AI voice calls that book meetings"
      ],
      "competitors": ["Apollo.io", "Outreach.io", "Salesloft"],
      "case_studies_url": "https://agentary.com/customers"
    },

    "icp": {
      "industries": ["SaaS", "Technology", "FinTech"],
      "company_size": { "min": 10, "max": 500 },
      "funding_stage": ["Seed", "Series A", "Series B"],
      "tech_stack_includes": ["Salesforce", "HubSpot"],
      "roles_to_target": ["VP Sales", "Head of Growth", "CRO", "CEO"],
      "geo": ["US", "Canada", "UK"],
      "exclude_companies": ["existing_customers_list"],
      "custom_rules": [
        "Company must have at least 3 SDRs (check job postings)",
        "Must NOT already use Outreach.io or Salesloft"
      ]
    },

    "persona": {
      "name": "Alex",
      "title": "Business Development",
      "tone": "professional but casual",
      "voice": "aoede",
      "approach": "consultative",
      "signature": "Alex from Agentary"
    },

    "channels": {
      "email": {
        "enabled": true,
        "daily_limit": 50,
        "from_address": "alex@agentary.com"
      },
      "linkedin": {
        "enabled": true,
        "daily_limit": 25
      },
      "voice": {
        "enabled": true,
        "daily_limit": 10,
        "only_for": "high_engagement"
      },
      "sms": {
        "enabled": false
      }
    },

    "sequence": {
      "steps": [
        { "day": 0, "channel": "email", "template": "intro" },
        { "day": 1, "channel": "linkedin", "action": "connect" },
        { "day": 3, "channel": "email", "template": "value_add" },
        { "day": 7, "channel": "email", "template": "social_proof" },
        { "day": 10, "channel": "voice", "template": "discovery_call" },
        { "day": 14, "channel": "email", "template": "breakup" }
      ],
      "pause_on_reply": true,
      "ab_test": true
    },

    "knowledge_base": {
      "product_docs_url": "https://docs.agentary.com",
      "faq_entries": [...],
      "objection_handlers": [...],
      "pricing_guide": "..."
    },

    "limits": {
      "max_leads_per_run": 50,
      "max_enrichments_per_day": 200,
      "max_research_per_run": 10,
      "monthly_budget": 500
    }
  }
}
```

---

# 10. UNIQUE DIFFERENTIATORS

## What Makes Agentary Different From Everything Else

### vs Apollo.io / ZoomInfo (Data providers)
- They give you data. Agentary gives you **autonomous agents that ACT on data**.
- They stop at "here's an email." Agentary **writes the email, sends it, follows up, calls them, and books the meeting.**

### vs Outreach.io / Salesloft (Sequence tools)
- They automate email sequences. Agentary has **AI voice calls that actually talk to prospects.**
- They require manual lead selection. Agentary **discovers leads autonomously.**
- They template messages. Agentary **generates unique messages from deep research.**

### vs Instantly / Smartlead (Cold email tools)
- They blast templated emails. Agentary **researches each prospect and writes unique messages.**
- They have no voice channel. Agentary **calls prospects with AI.**
- They don't qualify leads. Agentary **scores and qualifies automatically.**

### vs Clay (Enrichment + workflows)
- Clay is a spreadsheet. Agentary is an **autonomous agent platform.**
- Clay requires manual workflow building. Agentary **agents work autonomously.**
- Clay doesn't send outreach. Agentary **executes the entire pipeline.**

### vs 11x.ai / AiSDR (AI SDR tools)
- Closest competitors. But Agentary has:
  - **Real-time voice calling** (not just email)
  - **Open-source connectable architecture**
  - **Agent marketplace** for templates
  - **Self-hosted option** (privacy-conscious enterprises)
  - **Multi-channel sequences** (not just email)
  - **Intent signal detection** from multiple sources
  - **Conversation intelligence** with coaching

### THE AGENTARY MOAT (5 pillars)

```
1. VOICE-FIRST     — AI voice calls are the killer feature nobody else has
                     well-integrated with a complete sales stack.

2. RESEARCH-DEEP   — Not just data enrichment, but deep AI research
                     that produces actionable intelligence.

3. AGENT-NATIVE    — Not workflows-with-AI, but actual autonomous agents
                     with goals, memory, and decision-making.

4. FULL-STACK      — Discovery → Enrichment → Scoring → Research →
                     Outreach → Voice → Meeting → Pipeline → Analytics.
                     Nobody does ALL of this.

5. OPEN PLATFORM   — Agent marketplace, public API, webhooks,
                     self-hosted option. Build on top of Agentary.
```

---

# 11. IMPLEMENTATION PHASES

## Phase 0: Foundation (Week 1-2)
**Goal:** Rename, restructure, generalize core infrastructure

- [ ] Rename project: SecretAIRY → Agentary
- [ ] Rename models: Opportunity → Lead, Match → LeadScore, Dossier → IntelBrief
- [ ] Generalize Profile to ProductProfile
- [ ] Generalize match_engine → lead_scorer with configurable ICP rules
- [ ] Generalize outreach_gen → message_gen with product context
- [ ] Generalize dossier_gen → intel_gen for sales briefings
- [ ] Update all API routes and frontend references
- [ ] Create new Alembic migrations
- [ ] Update Docker configs and README

## Phase 1: Agent Engine MVP (Week 3-5)
**Goal:** Users can create and deploy autonomous agents

- [ ] Build Agent model and CRUD API
- [ ] Build AgentRun model and execution tracking
- [ ] Build agent_loop.py (generalized autopilot)
- [ ] Build ICP rule engine with configurable criteria
- [ ] Build agent configuration UI (dashboard)
- [ ] Build agent monitoring dashboard
- [ ] Wire up existing Scout as "Live Discovery" mode

## Phase 2: Enhanced Outreach (Week 6-8)
**Goal:** Multi-step sequences with A/B testing

- [ ] Build Sequence and SequenceStep models
- [ ] Build sequence_builder.py with timing + conditions
- [ ] Build sequence_executor.py with channel routing
- [ ] Build A/B testing for message variants
- [ ] Build reply detection and auto-pause
- [ ] Build sequence builder UI (drag-and-drop)
- [ ] Enhance message_gen with product-aware personalization

## Phase 3: Deal Pipeline & Analytics (Week 9-10)
**Goal:** Full CRM-lite with pipeline and analytics

- [ ] Build Deal model with Kanban stages
- [ ] Build deal_pipeline.py with auto-advance rules
- [ ] Build Kanban board UI
- [ ] Enhance analytics with agent/campaign/channel breakdowns
- [ ] Build activity timeline per lead/contact
- [ ] Build win/loss tracking

## Phase 4: Conversation Intelligence (Week 11-12)
**Goal:** Deep call analytics and coaching

- [ ] Build call_analyzer.py (sentiment, objections, talk ratio)
- [ ] Build coaching_engine.py (suggestions from patterns)
- [ ] Build call analytics dashboard
- [ ] Build objection library from transcripts
- [ ] Enhance voice prompts with objection handlers

## Phase 5: Integrations & Team (Week 13-16)
**Goal:** CRM sync, calendar, teams

- [ ] Build HubSpot bidirectional sync
- [ ] Build Google Calendar / Cal.com integration
- [ ] Build Organization + Team models
- [ ] Build roles/permissions system
- [ ] Build team invitation flow
- [ ] Build Slack notification integration

## Phase 6: Platform & Growth (Week 17-20)
**Goal:** Marketplace, billing, API

- [ ] Build agent template marketplace
- [ ] Build Stripe billing integration
- [ ] Build public API with API keys
- [ ] Build onboarding wizard
- [ ] Build white-label support
- [ ] Launch beta

---

# 12. TECHNICAL SPECIFICATIONS

## 12.1 Tech Stack (Final)

| Layer | Technology | Status |
|-------|-----------|--------|
| **Frontend** | Next.js 14, React 18, Tailwind CSS | Keep |
| **API** | FastAPI, Pydantic, SQLAlchemy | Keep |
| **Database** | PostgreSQL 16 | Keep |
| **Cache** | Redis 7 | Keep |
| **Vector DB** | Qdrant | Keep |
| **LLM** | Gemini 2.5 Flash | Keep |
| **Voice** | Pipecat + Gemini Live + Twilio | Keep |
| **Email** | Resend | Keep |
| **Embeddings** | Gemini embedding-001 (3072d) | Keep |
| **Search** | Exa API | Keep |
| **Enrichment** | Apollo, Clearbit, Hunter (NEW) | Build |
| **CRM** | HubSpot, Salesforce (NEW) | Build |
| **Calendar** | Cal.com, Google Calendar (NEW) | Build |
| **Billing** | Stripe (NEW) | Build |
| **Task Queue** | Celery + Redis (NEW) | Build |
| **Notifications** | Slack, Email (NEW) | Build |
| **Deployment** | Docker Compose → Kubernetes | Migrate |
| **Monitoring** | Sentry, Prometheus, Grafana (NEW) | Build |

## 12.2 API Design (New Routes)

```
# Agent Management
POST   /api/agents                    # Create agent
GET    /api/agents                    # List agents
GET    /api/agents/{id}               # Get agent
PUT    /api/agents/{id}               # Update agent config
DELETE /api/agents/{id}               # Delete agent
POST   /api/agents/{id}/deploy        # Deploy/activate agent
POST   /api/agents/{id}/pause         # Pause agent
GET    /api/agents/{id}/runs          # List agent runs
GET    /api/agents/{id}/runs/{run_id} # Get run details
GET    /api/agents/{id}/metrics       # Agent performance metrics

# Lead Management
POST   /api/leads                     # Import leads
GET    /api/leads                     # List leads (filterable)
GET    /api/leads/{id}                # Get lead details
PUT    /api/leads/{id}                # Update lead
POST   /api/leads/{id}/enrich         # Trigger enrichment
GET    /api/leads/{id}/timeline       # Interaction timeline
GET    /api/leads/{id}/signals        # Intent signals

# Sequence Management
POST   /api/sequences                 # Create sequence
GET    /api/sequences                 # List sequences
PUT    /api/sequences/{id}            # Update sequence
DELETE /api/sequences/{id}            # Delete sequence
POST   /api/sequences/{id}/enroll     # Enroll contacts
POST   /api/sequences/{id}/pause      # Pause sequence

# Deal Pipeline
GET    /api/deals                     # List deals
POST   /api/deals                     # Create deal
PUT    /api/deals/{id}                # Update deal
PUT    /api/deals/{id}/stage          # Move stage
GET    /api/deals/pipeline            # Pipeline summary
GET    /api/deals/forecast            # Revenue forecast

# Team Management
POST   /api/orgs                      # Create organization
GET    /api/orgs/{id}/members         # List members
POST   /api/orgs/{id}/invite          # Invite member
PUT    /api/orgs/{id}/members/{uid}   # Update member role

# Marketplace
GET    /api/marketplace/templates     # Browse templates
POST   /api/marketplace/templates     # Publish template
POST   /api/marketplace/templates/{id}/deploy  # Deploy template

# Keep existing routes (renamed where needed):
# /api/auth/*
# /api/profile/*          → /api/product-profile/*
# /api/contacts/*
# /api/campaigns/*        → /api/outreach/*
# /api/research/*
# /api/analytics/*
# /api/autopilot/*        → (absorbed into /api/agents)
# /api/scout/*            → /api/live-feed/*
# /voice/outbound/*
# /webhooks/*
```

## 12.3 Environment Variables (New)

```bash
# New for Agentary
APOLLO_API_KEY=          # Apollo.io enrichment
CLEARBIT_API_KEY=        # Clearbit enrichment
HUNTER_API_KEY=          # Hunter.io email finder
HUBSPOT_API_KEY=         # HubSpot CRM sync
SALESFORCE_CLIENT_ID=    # Salesforce OAuth
SALESFORCE_CLIENT_SECRET=
CALCOM_API_KEY=          # Cal.com scheduling
STRIPE_SECRET_KEY=       # Billing
STRIPE_WEBHOOK_SECRET=   # Stripe webhooks
SLACK_BOT_TOKEN=         # Slack notifications
SENTRY_DSN=              # Error tracking
```

---

# APPENDIX A: NAMING CONVENTIONS

```
SecretAIRY Term    →    Agentary Term
─────────────────────────────────────
Opportunity        →    Lead
Match              →    LeadScore
Dossier            →    IntelBrief
Profile            →    ProductProfile
CallCampaign       →    OutreachCampaign
Autopilot          →    AgentLoop
Scout              →    LiveDiscovery
Pipeline Stage     →    Deal Stage
Ingest             →    Discover
```

# APPENDIX B: COMPETITIVE LANDSCAPE

```
┌──────────────────────────────────────────────────────────────┐
│                 COMPETITIVE LANDSCAPE MAP                     │
│                                                               │
│  DATA PROVIDERS          SEQUENCE TOOLS          AI SDR       │
│  ┌─────────────┐        ┌─────────────┐        ┌──────────┐ │
│  │ Apollo.io    │        │ Outreach.io  │        │ 11x.ai   │ │
│  │ ZoomInfo     │        │ Salesloft    │        │ AiSDR    │ │
│  │ Clearbit     │        │ Instantly    │        │ Regie.ai │ │
│  │ Lusha        │        │ Smartlead    │        │ Lavender │ │
│  └─────────────┘        └─────────────┘        └──────────┘ │
│        │                       │                      │       │
│        │    ENRICHMENT         │                      │       │
│        │    ┌──────────┐       │                      │       │
│        │    │  Clay     │       │                      │       │
│        │    │  Clearout │       │                      │       │
│        │    └──────────┘       │                      │       │
│        │         │             │                      │       │
│        └─────────┴─────────────┴──────────────────────┘       │
│                              │                                │
│                     ┌────────▼────────┐                       │
│                     │                 │                       │
│                     │   AGENTARY      │                       │
│                     │                 │                       │
│                     │  Does ALL of    │                       │
│                     │  the above +    │                       │
│                     │  AI VOICE       │                       │
│                     │  CALLS          │                       │
│                     │                 │                       │
│                     └─────────────────┘                       │
│                                                               │
│  UNIQUE AGENTARY ADVANTAGES:                                  │
│  ✓ Full pipeline (discover → close)                          │
│  ✓ AI voice calls with real conversation                     │
│  ✓ Deep research (not just data)                             │
│  ✓ Autonomous agents (not just workflows)                    │
│  ✓ Agent marketplace                                         │
│  ✓ Self-hosted option                                        │
│  ✓ Open API platform                                         │
└──────────────────────────────────────────────────────────────┘
```

# APPENDIX C: PRICING MODEL (PROPOSED)

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENTARY PRICING                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FREE (Starter)           $0/mo                              │
│  • 1 agent                                                   │
│  • 100 leads/month                                           │
│  • 50 emails/month                                           │
│  • 0 voice calls                                             │
│  • Basic analytics                                           │
│                                                              │
│  PRO (Solo)               $79/mo                             │
│  • 3 agents                                                  │
│  • 1,000 leads/month                                         │
│  • 500 emails/month                                          │
│  • 50 voice calls/month                                      │
│  • Full analytics                                            │
│  • Sequence builder                                          │
│  • CRM sync (1)                                              │
│                                                              │
│  BUSINESS (Team)          $199/mo per seat                   │
│  • Unlimited agents                                          │
│  • 5,000 leads/month                                         │
│  • 2,000 emails/month                                        │
│  • 200 voice calls/month                                     │
│  • Team workspace                                            │
│  • Priority support                                          │
│  • All integrations                                          │
│  • A/B testing                                               │
│                                                              │
│  ENTERPRISE                Custom                            │
│  • Self-hosted option                                        │
│  • White-label                                               │
│  • Custom integrations                                       │
│  • SLA + dedicated support                                   │
│  • SSO/SAML                                                  │
│  • Unlimited everything                                      │
│                                                              │
│  ADD-ONS (usage-based):                                      │
│  • Extra voice minutes: $0.15/min                            │
│  • Extra enrichments: $0.05/lead                             │
│  • Extra AI credits: $0.01/request                           │
└─────────────────────────────────────────────────────────────┘
```

---

## WHAT TO COMMIT NEXT

### Immediate Actions (This Week)

1. **This document** — Commit as `docs/AGENTARY_PIVOT.md`
2. **Rename the project** — Update package.json, pyproject.toml, README, Docker files
3. **Create the new model schemas** — Agent, Lead, LeadScore, Sequence, Deal, Organization
4. **Generalize existing services** — match_engine → lead_scorer, dossier_gen → intel_gen
5. **Update frontend routes** — Rename pages to match new domain language
6. **Create migration plan** — Alembic migrations for schema changes

### The "Big Bang" First Commit

```
feat: pivot SecretAIRY → Agentary — AI sales agent platform

- Rename all models from job-search to sales domain
- Generalize ICP scoring engine (was: job match engine)
- Generalize intel brief generation (was: interview dossier)
- Generalize outreach generation (was: job cold outreach)
- Add Agent model and CRUD API
- Add ProductProfile (was: Resume Profile)
- Add Lead model (was: Opportunity)
- Add Deal pipeline (was: Job pipeline)
- Update all frontend routes and components
- Update Docker, Nginx, README
```

---

*This document is the complete blueprint for transforming SecretAIRY into Agentary. Every feature, every module, every architecture decision is documented here. Let's build.*
