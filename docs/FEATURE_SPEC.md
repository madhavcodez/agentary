# SecretAIRY Feature Specification

**Date:** 2026-03-19
**Status:** Draft -- ready for implementation prioritization
**Stack:** FastAPI + Next.js 14 + Gemini 2.5 Flash + Twilio + Exa + Qdrant + PostgreSQL + Redis

---

## Prioritized Feature List

Features are ranked by **Priority Score = Impact x Feasibility** (each 1--5 scale). Top features first.

---

## TIER 1: HIGH PRIORITY (Score >= 16)

---

### 1. Automated Follow-Up Email Sequences

**Priority Score: 25** (Impact: 5 | Feasibility: 5)

**Why:** The single highest-leverage feature. Every top outreach tool (Instantly, Lemlist, Smartlead, Apollo) treats automated follow-ups as table stakes. SecretAIRY already generates email drafts and sends via Resend -- this just adds a scheduler on top. Without it, every follow-up requires manual intervention, which defeats the "autopilot" value proposition.

**Implementation approach:**

- **New model:** `backend/app/models/email_sequence.py`
  ```
  EmailSequenceStep:
    id: UUID PK
    campaign_id: FK -> call_campaigns.id
    step_number: int (1, 2, 3...)
    delay_days: int (e.g., 3 = send 3 days after previous step)
    subject: str | null (null = reply to same thread)
    body: str
    status: enum(pending, sent, skipped, cancelled)
    sent_at: datetime | null
    created_at: datetime
  ```
- **New service:** `backend/app/services/email_sequencer.py`
  - `generate_followup_variants(db, campaign, step_number) -> EmailSequenceStep` -- Gemini generates contextual follow-ups that reference the original email, using tone escalation (friendly reminder -> value-add -> breakup email)
  - `process_email_queue(db) -> int` -- called by APScheduler every 15 minutes; queries steps where `status=pending AND created_at + delay_days <= now AND campaign has no reply`; sends via Resend; updates status
- **Resend reply detection:** Use Resend webhook `email.replied` event (or check `email.opened` + manual reply tracking via unique `Reply-To` address per campaign) to mark sequence as complete and skip remaining steps
- **Default sequence:** 3 steps at day 0 (initial), day 3 (follow-up), day 7 (breakup). Configurable per campaign.
- **Scheduler integration:** Add job to existing `backend/app/services/scheduler.py` -- `scheduler.add_job(_process_email_queue, "interval", minutes=15)`
- **Frontend:** Add "Sequence" tab in campaign detail view showing step timeline with status dots

**Dependencies:** Resend email sending (already planned), Resend webhooks (Feature #2)
**Time estimate:** 2--3 days

---

### 2. Resend Webhook Integration (Open/Click/Bounce Tracking)

**Priority Score: 25** (Impact: 5 | Feasibility: 5)

**Why:** Without delivery feedback, you are sending emails into a black hole. Resend natively supports 15 webhook event types including `email.delivered`, `email.opened`, `email.clicked`, `email.bounced`, `email.complained`. This data powers follow-up logic, domain reputation monitoring, and analytics. Every competitor has this.

**Implementation approach:**

- **New model:** `backend/app/models/email_event.py`
  ```
  EmailEvent:
    id: UUID PK
    campaign_id: FK -> call_campaigns.id
    resend_email_id: str (Resend's ID)
    event_type: str (delivered, opened, clicked, bounced, complained, ...)
    payload: JSON
    created_at: datetime
  ```
- **New API route:** `backend/app/api/webhooks.py`
  - `POST /webhooks/resend` -- receives Resend webhook payload, verifies signature using the webhook signing secret, stores `EmailEvent`, triggers side effects:
    - `email.bounced` -> mark contact email as invalid, skip future sends
    - `email.opened` -> update campaign stage (see Pipeline feature)
    - `email.complained` -> add to suppression list, never email again
    - `email.delivered` -> update `EmailSequenceStep.status = "delivered"`
  - Webhook signature verification: Resend sends a `svix-signature` header; verify using `svix` Python library (`pip install svix`)
- **Config addition:** Add `RESEND_WEBHOOK_SECRET` to `backend/app/config.py`
- **Suppression list:** New table `email_suppressions` with `email: str UNIQUE, reason: str, created_at`. Check before every send.
- **Frontend:** Show delivery status icons on campaign cards (delivered/opened/bounced)

**Dependencies:** Resend API key configured (already in config)
**Time estimate:** 1--2 days

---

### 3. CRM Pipeline Stages with Auto-Advance

**Priority Score: 20** (Impact: 5 | Feasibility: 4)

**Why:** SecretAIRY tracks match `status` as a simple string ("new") but has no progression model. Users cannot visualize where contacts are in their pipeline. Every CRM and outreach tool has stages. Auto-advancing based on events (email opened = "aware", replied = "engaged") eliminates manual busywork.

**Implementation approach:**

- **Pipeline stages enum:** Define in `backend/app/models/match.py` or new `pipeline.py`:
  ```
  PipelineStage = Enum:
    LEAD          # match found, no outreach yet
    CONTACTED     # first email/call sent
    AWARE         # email opened OR call connected
    ENGAGED       # replied to email OR call outcome = "connected"
    MEETING       # meeting scheduled (via calendar integration or manual)
    CLOSED_WON    # got the job/interview
    CLOSED_LOST   # rejected or ghosted
    PAUSED        # manually paused
  ```
- **Add to Match model:** `pipeline_stage: str = "lead"`, `stage_changed_at: datetime`
- **Auto-advance triggers:** Add to `backend/app/services/pipeline_engine.py`:
  - Campaign created for this match -> `CONTACTED`
  - Resend webhook `email.opened` -> `AWARE` (only advance forward, never backward)
  - Resend webhook `email.replied` or call outcome "connected" -> `ENGAGED`
  - Manual override via API for `MEETING`, `CLOSED_WON`, `CLOSED_LOST`
- **Stage transition log:** `pipeline_transitions` table: `match_id, from_stage, to_stage, trigger, created_at` -- audit trail
- **API endpoints:**
  - `PUT /matches/{id}/stage` -- manual stage update
  - `GET /matches/pipeline-summary` -- returns count per stage for dashboard
- **Frontend: Kanban board** -- new page `/pipeline` with drag-and-drop columns per stage. Use `@hello-pangea/dnd` (MIT, successor to react-beautiful-dnd). Each card shows company, role, score, contact name, last activity.

**Dependencies:** Resend webhooks (Feature #2) for auto-advance; works without them via manual updates
**Time estimate:** 3--4 days (2 backend, 1--2 frontend Kanban)

---

### 4. Contact Duplicate Detection (Fuzzy Matching)

**Priority Score: 20** (Impact: 4 | Feasibility: 5)

**Why:** The Exa contact discovery in `research/exa_search.py` already creates contacts automatically, and the current dedup in `research/engine.py` only checks exact `(company, name)` match. "Jane Smith" vs "Jane A. Smith" or "J. Smith" will create duplicates. At scale, duplicate contacts cause duplicate outreach -- embarrassing and damaging.

**Implementation approach:**

- **Library:** `rapidfuzz` (MIT, C++ backed, fast). Add to `requirements.txt`.
- **New service:** `backend/app/services/contact_dedup.py`
  ```python
  from rapidfuzz import fuzz, process

  def find_duplicates(
      db: Session, name: str, company: str, email: str | None = None,
      threshold: int = 85
  ) -> list[Contact]:
      # Stage 1: Exact email match (strongest signal)
      if email:
          exact = db.query(Contact).filter(
              func.lower(Contact.email) == email.lower()
          ).all()
          if exact:
              return exact

      # Stage 2: Fuzzy name+company match
      company_contacts = db.query(Contact).filter(
          func.lower(Contact.company) == company.lower()
      ).all()

      matches = []
      for c in company_contacts:
          name_score = fuzz.token_sort_ratio(
              _normalize(name), _normalize(c.name or "")
          )
          if name_score >= threshold:
              matches.append(c)
      return matches

  def _normalize(s: str) -> str:
      return re.sub(r"[^a-z\s]", "", s.lower()).strip()
  ```
- **Integration points:**
  - Call `find_duplicates` in `research/engine.py` before creating new contacts (replace the exact-match check on line 127-133)
  - Call in `POST /contacts` endpoint to warn user: return `{"warning": "Possible duplicate", "existing": [...]}`
  - Add `GET /contacts/duplicates` endpoint that scans all contacts and returns clusters
- **Frontend:** Show yellow warning badge on contact cards when potential duplicates exist

**Dependencies:** None
**Time estimate:** 1 day

---

### 5. A/B Testing Subject Lines with Gemini Variants

**Priority Score: 20** (Impact: 5 | Feasibility: 4)

**Why:** Subject lines determine open rates (40--60% is the 2026 benchmark for warmed lists). AI-generated A/B testing is a defining feature of tools like Instantly and Lemlist. SecretAIRY already uses Gemini to generate email subjects -- extending this to generate 2--4 variants and track which performs best is high-impact and architecturally simple.

**Implementation approach:**

- **Variant generation:** Extend `backend/app/services/outreach_gen.py` `_gen_email_draft`:
  ```python
  async def _gen_email_variants(context: str, num_variants: int = 3) -> list[dict]:
      prompt = f"""Generate {num_variants} distinct cold outreach email variants.
      Each should have a DIFFERENT subject line strategy:
      1. Question-based (curiosity)
      2. Value-proposition (benefit)
      3. Social proof / specificity (reference a fact)

      {context}

      Return JSON array: [{{"subject": "...", "body": "...", "strategy": "..."}}]"""
      result = await generate_structured(prompt, schema_hint="[...]")
      return result if isinstance(result, list) else [result]
  ```
- **New model fields on `CallCampaign`:**
  - `email_variants: JSON` -- stores array of `{subject, body, strategy}`
  - `active_variant_index: int = 0`
- **Splitting logic:** When sending to multiple contacts at the same company, rotate variants. When sending a sequence, use the variant with the highest open rate from previous sends.
- **Winner selection:** After N sends per variant (minimum 50, per best practice), compare open rates from `EmailEvent` data. Auto-select winner for remaining sends.
- **API:** `POST /campaigns/{id}/generate-variants` -> returns array of variants. `PUT /campaigns/{id}/select-variant` -> set active variant.
- **Frontend:** In the "Email Draft" expanded section, show tabs for each variant with strategy label and open rate percentage

**Dependencies:** Resend webhooks (Feature #2) for open rate tracking
**Time estimate:** 2--3 days

---

### 6. Analytics Dashboard (Outreach Funnel + Channel Comparison)

**Priority Score: 20** (Impact: 5 | Feasibility: 4)

**Why:** Without analytics, the user cannot answer "Is SecretAIRY working?" The data already exists in the database (campaigns, email events, call logs, matches) -- it just needs aggregation and visualization.

**Implementation approach:**

- **New API route:** `backend/app/api/analytics.py`
  ```python
  @router.get("/analytics/funnel")
  def get_funnel(db, days: int = 30):
      cutoff = datetime.utcnow() - timedelta(days=days)
      return {
          "matches_found": db.query(Match).filter(Match.created_at >= cutoff).count(),
          "contacted": db.query(Match).filter(
              Match.pipeline_stage.in_(["contacted","aware","engaged","meeting","closed_won"]),
              Match.created_at >= cutoff
          ).count(),
          "opened": db.query(EmailEvent).filter(
              EmailEvent.event_type == "opened",
              EmailEvent.created_at >= cutoff
          ).distinct(EmailEvent.campaign_id).count(),
          "replied": db.query(EmailEvent).filter(
              EmailEvent.event_type == "replied",
              EmailEvent.created_at >= cutoff
          ).distinct(EmailEvent.campaign_id).count(),
          "meetings": db.query(Match).filter(
              Match.pipeline_stage == "meeting",
              Match.stage_changed_at >= cutoff
          ).count(),
      }

  @router.get("/analytics/channel-performance")
  def channel_performance(db, days: int = 30):
      # Compare email vs call effectiveness
      return {
          "email": {"sent": N, "opened": N, "replied": N, "rate": pct},
          "call": {"attempted": N, "connected": N, "meetings": N, "rate": pct},
      }

  @router.get("/analytics/activity-timeline")
  def activity_timeline(db, days: int = 30, granularity: str = "day"):
      # Time-series: emails_sent, calls_made, matches_found per day
      ...

  @router.get("/analytics/score-distribution")
  def score_distribution(db):
      # Histogram of match composite_score in 10-point buckets
      ...
  ```
- **Frontend:** New `/analytics` page with 4 sections:
  1. **Funnel chart** -- horizontal bar chart (matches -> contacted -> opened -> replied -> meeting). Use plain CSS or lightweight `recharts` library.
  2. **Channel comparison** -- side-by-side cards for email vs. call with key metrics
  3. **Activity timeline** -- line chart of daily outreach volume over last 30 days
  4. **Score distribution** -- bar chart of match quality
- **Nav update:** Add "Analytics" to `dashboard/components/Nav.tsx`

**Dependencies:** Resend webhooks (Feature #2) and Pipeline stages (Feature #3) for full funnel data. Partial analytics work without them using campaign/call data.
**Time estimate:** 2--3 days (1 backend, 1--2 frontend charts)

---

## TIER 2: MEDIUM-HIGH PRIORITY (Score 12--15)

---

### 7. Call Transcript Summarization & Outcome Classification via Gemini

**Priority Score: 15** (Impact: 5 | Feasibility: 3)

**Why:** `call_post_processor.py` already does this with Gemini, but it requires the transcript to be passed in. The gap is that SecretAIRY does not currently capture transcripts from Twilio calls. Closing this loop means every call automatically gets summarized, classified, and turned into next-step actions.

**Implementation approach:**

- **Twilio recording + transcription:** In `twilio_client.py` `initiate_call`, add to payload:
  ```python
  "Record": "true",
  "RecordingStatusCallback": f"{webhook_base}/voice/recording-callback",
  "RecordingStatusCallbackEvent": "completed",
  "TranscriptionType": "conversation",  # Twilio Media Streams
  ```
- **New webhook endpoint:** `POST /voice/recording-callback`
  - Receives recording URL from Twilio
  - Fetches recording, sends to Gemini for transcription (or uses Twilio's built-in transcription)
  - Calls existing `process_call_result(db, call_log, transcript)` from `call_post_processor.py`
- **Enhanced classification:** The existing `_CLASSIFICATION_SCHEMA` in `call_post_processor.py` is already solid. Add `sentiment: str (positive|neutral|negative)` and `key_quotes: [str]` fields.
- **Frontend:** In campaign detail page (`/calls/[id]/page.tsx`), show transcript accordion with highlighted key quotes, sentiment badge, and next-steps card.

**Dependencies:** Voice pipeline fix (already planned), Twilio paid account (for recording)
**Time estimate:** 2--3 days

---

### 8. Circuit Breaker Pattern for External APIs

**Priority Score: 15** (Impact: 5 | Feasibility: 3)

**Why:** SecretAIRY calls 5 external APIs (Gemini, Exa, Resend, Twilio, Qdrant). If Gemini goes down, the entire autopilot cycle fails, and the scheduler retries endlessly. A circuit breaker prevents cascading failures and preserves API rate limits. This is standard fintech-grade reliability.

**Implementation approach:**

- **Library:** `pybreaker==1.2.0` (MIT, production-proven). Add to `requirements.txt`.
- **New module:** `backend/app/services/circuit_breakers.py`
  ```python
  import pybreaker

  gemini_breaker = pybreaker.CircuitBreaker(
      fail_max=5,
      reset_timeout=60,  # seconds before half-open
      name="gemini",
  )

  exa_breaker = pybreaker.CircuitBreaker(
      fail_max=3,
      reset_timeout=120,
      name="exa",
  )

  resend_breaker = pybreaker.CircuitBreaker(
      fail_max=3,
      reset_timeout=60,
      name="resend",
  )

  twilio_breaker = pybreaker.CircuitBreaker(
      fail_max=3,
      reset_timeout=120,
      name="twilio",
  )

  qdrant_breaker = pybreaker.CircuitBreaker(
      fail_max=5,
      reset_timeout=30,
      name="qdrant",
  )

  ALL_BREAKERS = [gemini_breaker, exa_breaker, resend_breaker, twilio_breaker, qdrant_breaker]

  def get_breaker_statuses() -> dict[str, str]:
      return {b.name: b.current_state for b in ALL_BREAKERS}
  ```
- **Wrap external calls:** In `gemini.py`, wrap `generate_structured`, `generate_text`, `embed_text` with `@gemini_breaker`. In `twilio_client.py`, wrap `initiate_call` with `@twilio_breaker`. Same pattern for Exa and Qdrant.
- **Fallback behavior:** When breaker is open:
  - Gemini calls: return cached result or raise `ServiceUnavailable` with retry-after header
  - Qdrant calls: skip vector search, use LLM-only scoring
  - Twilio calls: re-queue campaign for later
- **Health check endpoint:** `GET /health/dependencies` returns status of each breaker (closed/open/half-open) plus last error time

**Dependencies:** None
**Time estimate:** 1--2 days

---

### 9. Contact Quality Scoring

**Priority Score: 15** (Impact: 3 | Feasibility: 5)

**Why:** Not all contacts are equal. A VP of Engineering is more valuable than a generic "careers@company.com" address. Scoring contacts lets the autopilot prioritize who to reach out to first.

**Implementation approach:**

- **Add to Contact model:** `quality_score: Float = 0.0`
- **Scoring function in `backend/app/services/contact_scorer.py`:**
  ```python
  def score_contact(contact: Contact) -> float:
      score = 0.0

      # Title relevance (0-0.4)
      title = (contact.title or "").lower()
      high_value = ["vp", "director", "head of", "hiring manager", "cto", "ceo"]
      mid_value = ["manager", "lead", "recruiter", "talent"]
      if any(t in title for t in high_value):
          score += 0.4
      elif any(t in title for t in mid_value):
          score += 0.25
      elif title:
          score += 0.1

      # Contact completeness (0-0.3)
      if contact.email:
          score += 0.15
      if contact.phone:
          score += 0.1
      if contact.name:
          score += 0.05

      # Source reliability (0-0.2)
      source_scores = {"exa": 0.15, "manual": 0.2, "linkedin": 0.2}
      score += source_scores.get(contact.source, 0.05)

      # Recency (0-0.1)
      age_days = (datetime.utcnow() - contact.created_at).days
      if age_days < 7:
          score += 0.1
      elif age_days < 30:
          score += 0.05

      return round(min(score, 1.0), 2)
  ```
- **Auto-score:** Call on contact creation and in autopilot cycle. Sort campaigns by contact quality score when processing call queue.
- **Frontend:** Show quality score badge on contact cards (green/amber/red)

**Dependencies:** None
**Time estimate:** 0.5 days

---

### 10. Hunter.io Email Verification Before Sending

**Priority Score: 15** (Impact: 5 | Feasibility: 3)

**Why:** Sending to invalid emails destroys domain reputation. Hunter.io email verification checks syntax, MX records, and SMTP responses. It costs 0.5 credits per call with a free tier of 50/month. This is the single most impactful deliverability improvement.

**Implementation approach:**

- **Config:** Add `HUNTER_API_KEY: str = ""` to `backend/app/config.py`
- **New service:** `backend/app/services/email_verifier.py`
  ```python
  import httpx
  from ..config import settings

  HUNTER_VERIFY_URL = "https://api.hunter.io/v2/email-verifier"

  async def verify_email(email: str) -> dict:
      if not settings.hunter_api_key:
          return {"status": "unknown", "reason": "Hunter API key not configured"}

      async with httpx.AsyncClient() as client:
          resp = await client.get(
              HUNTER_VERIFY_URL,
              params={"email": email, "api_key": settings.hunter_api_key},
              timeout=10.0,
          )
          resp.raise_for_status()
          data = resp.json().get("data", {})
          return {
              "status": data.get("status"),       # deliverable, undeliverable, risky, unknown
              "score": data.get("score"),          # 0-100
              "disposable": data.get("disposable"),
              "webmail": data.get("webmail"),
          }
  ```
- **Integration:** Call `verify_email` before `send_email` in campaign flow. If status is "undeliverable", skip send, mark contact email as invalid, log warning. If "risky", send but log for monitoring.
- **Fallback chain:** Exa finds contact -> Hunter verifies email -> if invalid, try to find alternative email via Hunter's Email Finder API (`/v2/email-finder` with domain + name) -> manual fallback
- **Rate limiting:** Hunter allows 10 req/s. Add `asyncio.sleep(0.1)` between calls. Use circuit breaker (Feature #8).
- **Cache results:** Store verification result in `Contact.email_verified: bool`, `Contact.email_verified_at: datetime` to avoid re-verifying

**Dependencies:** Hunter.io API key (paid plan or free tier)
**Time estimate:** 1--2 days

---

### 11. Slack Notifications for Key Events

**Priority Score: 12** (Impact: 4 | Feasibility: 3)

**Why:** Users should not need to poll the dashboard. Slack is where knowledge workers live. Notifications for high-value events (email reply received, call completed, high-score match found) create an interrupt-driven workflow.

**Implementation approach:**

- **Library:** `slack-sdk` (official, MIT). Add to `requirements.txt`.
- **Config:** Add `SLACK_WEBHOOK_URL: str = ""` to `backend/app/config.py`
- **New service:** `backend/app/services/slack_notifier.py`
  ```python
  from slack_sdk.webhook import WebhookClient
  from ..config import settings

  def _get_webhook() -> WebhookClient | None:
      if not settings.slack_webhook_url:
          return None
      return WebhookClient(url=settings.slack_webhook_url)

  def notify(title: str, message: str, color: str = "#4F46E5") -> None:
      webhook = _get_webhook()
      if not webhook:
          return
      webhook.send(
          attachments=[{
              "color": color,
              "title": title,
              "text": message,
              "footer": "SecretAIRY",
          }]
      )
  ```
- **Trigger points:** Integrate `notify()` calls into:
  - `webhooks.py` Resend handler: on `email.replied` -> "Email reply from {contact} at {company}"
  - `call_post_processor.py`: on call completion -> "Call to {contact} completed: {outcome}"
  - `match_engine.py`: when `composite_score >= 80` -> "High-score match: {title} at {company} (score: {score})"
  - `autopilot.py`: on cycle completion -> "Autopilot complete: {results summary}"
- **Non-blocking:** Wrap in `asyncio.to_thread()` or fire-and-forget to avoid blocking main flow

**Dependencies:** Slack workspace with incoming webhook configured
**Time estimate:** 1 day

---

### 12. Idempotency Keys on Mutating Operations

**Priority Score: 12** (Impact: 4 | Feasibility: 3)

**Why:** Network retries can cause double-sends, double-calls, duplicate campaign creation. Fintech-grade APIs use idempotency keys to ensure exactly-once semantics. SecretAIRY's most dangerous endpoints are `POST /campaigns/{id}/call-now` and `POST /campaigns/{id}/send-email`.

**Implementation approach:**

- **Library:** `fastapi-idempotent` or custom middleware. Custom is simpler for this codebase.
- **New table:** `idempotency_keys`
  ```
  key: str PK (client-provided UUID)
  endpoint: str
  request_hash: str
  response_body: JSON
  status_code: int
  created_at: datetime (with TTL -- delete after 24h)
  ```
- **Middleware:** `backend/app/middleware/idempotency.py`
  ```python
  class IdempotencyMiddleware:
      async def __call__(self, request, call_next):
          if request.method not in ("POST", "PUT", "PATCH"):
              return await call_next(request)

          idem_key = request.headers.get("Idempotency-Key")
          if not idem_key:
              return await call_next(request)

          # Check if key already exists
          existing = db.query(IdempotencyKey).filter_by(key=idem_key).first()
          if existing:
              return JSONResponse(
                  content=existing.response_body,
                  status_code=existing.status_code,
              )

          # Process request and store result
          response = await call_next(request)
          # Store response with key
          ...
          return response
  ```
- **Critical endpoints to protect:**
  - `POST /campaigns/{id}/call-now` -- prevents double-dialing
  - `POST /campaigns/{id}/send-email` -- prevents double-sending
  - `POST /campaigns` -- prevents duplicate campaign creation
  - `POST /autopilot/run` -- prevents concurrent autopilot runs (already has `_running` flag, but not durable)
- **Redis storage:** Use Redis with TTL for idempotency key storage (faster than PostgreSQL for this pattern, and Redis is already in the stack)
- **Client-side:** Update `dashboard/lib/api.ts` `request()` function to auto-generate and send `Idempotency-Key` header for POST/PUT requests

**Dependencies:** Redis (already in stack)
**Time estimate:** 1--2 days

---

## TIER 2: MEDIUM PRIORITY (Score 8--11)

---

### 13. Request/Response Audit Logging

**Priority Score: 12** (Impact: 4 | Feasibility: 3)

**Why:** The existing `ActionLog` model captures high-level events but not request/response pairs. For debugging failed outreach, investigating complaints, and compliance, you need a full audit trail of what was sent to whom and when.

**Implementation approach:**

- **Extend `ActionLog` model:** Add fields `request_body: JSON`, `response_body: JSON`, `endpoint: str`, `user_id: UUID (nullable for now)`
- **FastAPI middleware:** `backend/app/middleware/audit_log.py`
  - Log all mutating requests (POST, PUT, DELETE) to `action_logs` table
  - Exclude sensitive fields (API keys, auth tokens) via a deny-list
  - Include: endpoint, method, request body (sanitized), response status, timestamp
- **Async writing:** Use `BackgroundTasks` to write audit logs without blocking the response
- **Retention:** Add APScheduler job to delete audit logs older than 90 days

**Dependencies:** None
**Time estimate:** 1 day

---

### 14. Voicemail Detection and Automated Voicemail Drop

**Priority Score: 12** (Impact: 4 | Feasibility: 3)

**Why:** Many cold calls reach voicemail. Twilio's AMD (Answering Machine Detection) can detect this and automatically play a pre-recorded voicemail message. SecretAIRY already generates `voicemail_script` in `call_script_gen.py` -- this just connects the dots.

**Implementation approach:**

- **Enable AMD in `twilio_client.py`:** Uncomment and configure the `MachineDetection` parameter (currently disabled per code comment -- requires paid Twilio account):
  ```python
  "MachineDetection": "DetectMessageEnd",
  "MachineDetectionTimeout": 5000,
  "AsyncAmd": "true",
  "AsyncAmdStatusCallback": f"{webhook_base}/voice/amd-callback/{campaign_id}",
  ```
- **New webhook:** `POST /voice/amd-callback/{campaign_id}`
  - If `AnsweredBy == "machine_end_beep"`: Use Twilio `<Say>` or `<Play>` to deliver the voicemail script from `campaign.script_json["voicemail_script"]`
  - If `AnsweredBy == "human"`: Proceed with normal call flow
  - If `AnsweredBy == "machine_start"`: Hang up (no point leaving message before beep)
- **TTS voicemail:** Use Gemini TTS or Twilio's built-in `<Say voice="Polly.Matthew">` to speak the voicemail script
- **Call log update:** Set `outcome = "voicemail_left"` in CallLog

**Dependencies:** Twilio paid account, voice pipeline fix (already planned)
**Time estimate:** 1--2 days

---

### 15. Health Check Dashboard

**Priority Score: 10** (Impact: 2 | Feasibility: 5)

**Why:** Quick visibility into whether all external services are healthy. Simple to build, valuable for operations.

**Implementation approach:**

- **Enhance existing `/health` endpoint:**
  ```python
  @router.get("/health/detailed")
  async def detailed_health():
      checks = {}

      # PostgreSQL
      try:
          db.execute(text("SELECT 1"))
          checks["postgresql"] = "healthy"
      except: checks["postgresql"] = "unhealthy"

      # Redis
      try:
          redis.ping()
          checks["redis"] = "healthy"
      except: checks["redis"] = "unhealthy"

      # Qdrant
      try:
          qdrant_store.get_client().get_collections()
          checks["qdrant"] = "healthy"
      except: checks["qdrant"] = "unhealthy"

      # Circuit breaker statuses
      checks["circuit_breakers"] = get_breaker_statuses()

      # Scheduler
      checks["scheduler"] = "running" if scheduler.running else "stopped"

      return {"status": "healthy" if all(...) else "degraded", "checks": checks}
  ```
- **Frontend:** Small status bar at bottom of Nav showing green/yellow/red dot with hover tooltip

**Dependencies:** Circuit breakers (Feature #8) for full view
**Time estimate:** 0.5 days

---

### 16. Domain Reputation Monitoring

**Priority Score: 10** (Impact: 5 | Feasibility: 2)

**Why:** In 2025--2026, Google and Yahoo enforce strict sender policies. Monitoring bounce rates and complaint rates per sending domain prevents blacklisting. Critical for any serious email outreach.

**Implementation approach:**

- **Aggregation service:** `backend/app/services/domain_health.py`
  ```python
  def get_domain_health(db: Session, days: int = 7) -> dict:
      cutoff = datetime.utcnow() - timedelta(days=days)
      events = db.query(EmailEvent).filter(
          EmailEvent.created_at >= cutoff
      ).all()

      total_sent = len([e for e in events if e.event_type == "sent"])
      bounces = len([e for e in events if e.event_type == "bounced"])
      complaints = len([e for e in events if e.event_type == "complained"])

      bounce_rate = bounces / max(total_sent, 1)
      complaint_rate = complaints / max(total_sent, 1)

      # Thresholds from Google Postmaster guidelines
      return {
          "total_sent_7d": total_sent,
          "bounce_rate": bounce_rate,
          "bounce_status": "danger" if bounce_rate > 0.05 else "warning" if bounce_rate > 0.02 else "healthy",
          "complaint_rate": complaint_rate,
          "complaint_status": "danger" if complaint_rate > 0.003 else "warning" if complaint_rate > 0.001 else "healthy",
          "recommendation": _get_recommendation(bounce_rate, complaint_rate),
      }
  ```
- **Auto-throttle:** If bounce rate > 5%, automatically pause email sending and alert via Slack. Resume when rate drops below 2% over 24h rolling window.
- **API:** `GET /analytics/domain-health`
- **Frontend:** Red/yellow/green indicator on analytics dashboard

**Dependencies:** Resend webhooks (Feature #2)
**Time estimate:** 1 day

---

### 17. Webhook Endpoint for External Integrations

**Priority Score: 10** (Impact: 2 | Feasibility: 5)

**Why:** Allows integration with Zapier, Make, n8n, or custom systems. Low effort, opens extensibility.

**Implementation approach:**

- **New table:** `webhook_subscriptions`
  ```
  id: UUID PK
  url: str (customer's webhook URL)
  events: JSON (array of event types to subscribe to)
  secret: str (for HMAC signing)
  is_active: bool
  created_at: datetime
  ```
- **Event types:** `match.high_score`, `email.replied`, `call.completed`, `campaign.created`, `autopilot.completed`
- **Dispatch service:** `backend/app/services/webhook_dispatcher.py`
  - On each event, query active subscriptions matching the event type
  - POST JSON payload to subscriber URL with HMAC-SHA256 signature in `X-Signature` header
  - Retry 3 times with exponential backoff on failure
  - Log delivery status
- **API:** `POST /webhook-subscriptions`, `GET /webhook-subscriptions`, `DELETE /webhook-subscriptions/{id}`

**Dependencies:** None
**Time estimate:** 1--2 days

---

### 18. Dead Letter Queue for Failed Operations

**Priority Score: 10** (Impact: 4 | Feasibility: 2.5)

**Why:** When email sending fails, call initiation fails, or Gemini returns an error, the operation is lost. A DLQ captures failed operations for retry or manual intervention.

**Implementation approach:**

- **New table:** `dead_letter_queue`
  ```
  id: UUID PK
  operation_type: str (send_email, initiate_call, generate_content, etc.)
  payload: JSON (full request data needed to retry)
  error_message: str
  retry_count: int = 0
  max_retries: int = 3
  status: str (pending, retrying, exhausted, resolved)
  created_at: datetime
  resolved_at: datetime | null
  ```
- **Integration:** Wrap critical operations in try/except; on failure, insert into DLQ:
  ```python
  except Exception as e:
      dlq_entry = DeadLetterEntry(
          operation_type="send_email",
          payload={"campaign_id": str(campaign.id), "email": contact.email, ...},
          error_message=str(e),
      )
      db.add(dlq_entry)
      db.commit()
  ```
- **Retry worker:** APScheduler job every 5 minutes; picks up `status=pending` entries with `retry_count < max_retries`; retries the operation; increments retry_count; marks as `resolved` on success or `exhausted` on final failure
- **API:** `GET /admin/dlq` -- list failed operations. `POST /admin/dlq/{id}/retry` -- manual retry.
- **Frontend:** Admin section showing DLQ entries with retry button

**Dependencies:** None
**Time estimate:** 2 days

---

## TIER 3: LOWER PRIORITY (Score <= 8)

---

### 19. Twilio Conversational Intelligence Integration

**Priority Score: 9** (Impact: 3 | Feasibility: 3)

**Why:** Twilio Conversational Intelligence provides production-grade sentiment analysis, topic detection, and call scoring out of the box. However, SecretAIRY already does classification via Gemini in `call_post_processor.py`, making this partially redundant.

**Implementation approach:**

- Enable Twilio Conversational Intelligence in Twilio console
- After each call recording, submit to the Transcript Resource API
- Apply pre-built Language Operators: Sentiment, Summary, Task Completion
- Store results alongside existing Gemini classification for comparison
- Over time, compare accuracy and cost; pick the better system

**Dependencies:** Twilio paid account with Conversational Intelligence add-on (additional cost)
**Time estimate:** 2 days

---

### 20. Request Rate Limiting Per User

**Priority Score: 8** (Impact: 4 | Feasibility: 2)

**Why:** Once multi-tenancy is added, you need per-user rate limits to prevent abuse. Before auth exists, this is premature.

**Implementation approach:**

- **Library:** `slowapi` (built on `limits`, works with FastAPI)
- **Integration:** Add as middleware after auth is implemented
  ```python
  from slowapi import Limiter
  limiter = Limiter(key_func=get_user_id_from_token)
  app.state.limiter = limiter

  @router.post("/campaigns/{id}/call-now")
  @limiter.limit("5/minute")
  async def call_now(...):
  ```
- **Default limits:** 60 req/min general, 5/min for expensive operations (call, send-email, autopilot)

**Dependencies:** Auth system (already planned)
**Time estimate:** 0.5 days (once auth exists)

---

### 21. Input Sanitization Beyond Pydantic

**Priority Score: 8** (Impact: 4 | Feasibility: 2)

**Why:** Pydantic validates types but not content. Email drafts could contain XSS payloads that render in the dashboard. Contact names could contain SQL injection attempts (though SQLAlchemy parameterizes, defense in depth matters).

**Implementation approach:**

- **Library:** `bleach` for HTML sanitization, or the modern `nh3` (Rust-backed, faster)
- **Sanitization middleware:** `backend/app/middleware/sanitize.py`
  - Strip HTML tags from all string inputs in POST/PUT bodies
  - Reject inputs containing `<script>`, `javascript:`, `data:text/html` patterns
  - Normalize unicode to prevent homoglyph attacks
- **Email draft exception:** Email bodies may legitimately contain HTML. Sanitize on display (frontend), not on storage. Use React's default XSS protection (no `dangerouslySetInnerHTML`).
- **CSP headers:** Add Content-Security-Policy headers via FastAPI middleware:
  ```python
  @app.middleware("http")
  async def add_security_headers(request, call_next):
      response = await call_next(request)
      response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
      response.headers["X-Content-Type-Options"] = "nosniff"
      response.headers["X-Frame-Options"] = "DENY"
      return response
  ```

**Dependencies:** None
**Time estimate:** 1 day

---

### 22. PII Detection and Masking in Logs

**Priority Score: 8** (Impact: 4 | Feasibility: 2)

**Why:** Call transcripts and email bodies contain names, phone numbers, emails. These appear in logs. GDPR/CCPA compliance requires PII to be masked or redacted in logs.

**Implementation approach:**

- **Custom log filter:** `backend/app/logging_filter.py`
  ```python
  import re
  import logging

  PII_PATTERNS = {
      "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL_REDACTED]"),
      "phone": (r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_REDACTED]"),
      "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
  }

  class PIIMaskingFilter(logging.Filter):
      def filter(self, record):
          if isinstance(record.msg, str):
              for name, (pattern, replacement) in PII_PATTERNS.items():
                  record.msg = re.sub(pattern, replacement, record.msg)
          return True
  ```
- **Attach filter:** Add to root logger in `main.py`:
  ```python
  logging.getLogger().addFilter(PIIMaskingFilter())
  ```
- **Existing PII patterns:** The voice policy engine at `backend/app/voice/policy/rules.py` already defines `PII_PATTERNS`. Reuse those patterns for consistency.

**Dependencies:** None
**Time estimate:** 0.5 days

---

### 23. API Key Rotation Support

**Priority Score: 6** (Impact: 3 | Feasibility: 2)

**Why:** When an API key is compromised, you need to rotate without downtime. Currently all keys are single env vars with no rotation mechanism.

**Implementation approach:**

- **Dual-key support:** For each external API key in config, support a primary and fallback:
  ```python
  gemini_api_key: str = ""
  gemini_api_key_fallback: str = ""
  ```
- **Rotation logic:** Try primary key first. On auth failure (401/403), try fallback. If fallback works, log alert that primary key is invalid.
- **Internal API keys:** Once auth is added, support API key revocation and generation via `POST /auth/api-keys` and `DELETE /auth/api-keys/{id}`

**Dependencies:** Auth system (already planned)
**Time estimate:** 1 day

---

### 24. CORS Strict Mode

**Priority Score: 6** (Impact: 3 | Feasibility: 2)

**Why:** The current CORS config likely allows all origins in dev mode. Production needs strict CORS.

**Implementation approach:**

- **Config:** Add `CORS_ORIGINS: str = "http://localhost:3000"` to config
- **Middleware update:**
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.cors_origins.split(","),
      allow_credentials=True,
      allow_methods=["GET", "POST", "PUT", "DELETE"],
      allow_headers=["*"],
  )
  ```

**Dependencies:** None
**Time estimate:** 0.25 days

---

## Implementation Order (Recommended Roadmap)

### Sprint 1 (Week 1): Foundation -- 5 days
1. **Resend Webhooks** (#2) -- 1.5 days -- unlocks everything email-related
2. **Contact Dedup** (#4) -- 1 day -- quick win, prevents data quality issues
3. **Contact Quality Scoring** (#9) -- 0.5 days -- quick win
4. **Circuit Breakers** (#8) -- 1.5 days -- reliability foundation
5. **Health Check Dashboard** (#15) -- 0.5 days -- operational visibility

### Sprint 2 (Week 2): Email Intelligence -- 5 days
1. **Automated Follow-Up Sequences** (#1) -- 2.5 days -- highest impact feature
2. **A/B Testing Subject Lines** (#5) -- 2.5 days -- differentiator

### Sprint 3 (Week 3): Pipeline + Analytics -- 5 days
1. **Pipeline Stages + Auto-Advance** (#3) -- 3 days -- CRM backbone
2. **Analytics Dashboard** (#6) -- 2 days -- proves ROI

### Sprint 4 (Week 4): Reliability + Integrations -- 5 days
1. **Idempotency Keys** (#12) -- 1.5 days
2. **Slack Notifications** (#11) -- 1 day
3. **Hunter.io Email Verification** (#10) -- 1.5 days
4. **Dead Letter Queue** (#18) -- 1 day (simplified version)

### Sprint 5 (Week 5): Call Intelligence + Hardening -- 5 days
1. **Call Transcript Capture + Summarization** (#7) -- 2.5 days
2. **Voicemail Detection + Drop** (#14) -- 1.5 days
3. **Audit Logging** (#13) -- 0.5 days
4. **PII Masking** (#22) -- 0.5 days

### Sprint 6 (Week 6): Polish -- as needed
1. Domain Reputation Monitoring (#16)
2. Webhook Endpoint for External Integrations (#17)
3. Input Sanitization (#21)
4. Rate Limiting (#20)
5. CORS Strict Mode (#24)
6. API Key Rotation (#23)

---

## New Dependencies Summary

| Package | Purpose | License | PyPI |
|---------|---------|---------|------|
| `svix` | Resend webhook signature verification | MIT | yes |
| `rapidfuzz` | Fuzzy contact deduplication | MIT | yes |
| `pybreaker` | Circuit breaker pattern | BSD | yes |
| `slack-sdk` | Slack notifications | MIT | yes |
| `nh3` | HTML sanitization | MIT | yes |
| `slowapi` | Rate limiting (post-auth) | MIT | yes |

| npm Package | Purpose | License |
|-------------|---------|---------|
| `@hello-pangea/dnd` | Kanban drag-and-drop | Apache 2.0 |
| `recharts` | Analytics charts | MIT |

---

## New Database Tables Summary

| Table | Purpose | Feature # |
|-------|---------|-----------|
| `email_sequence_steps` | Follow-up email steps per campaign | #1 |
| `email_events` | Resend webhook event storage | #2 |
| `email_suppressions` | Bounced/complained email blocklist | #2 |
| `pipeline_transitions` | Stage change audit trail | #3 |
| `idempotency_keys` | Exactly-once request dedup (Redis) | #12 |
| `dead_letter_queue` | Failed operation retry queue | #18 |
| `webhook_subscriptions` | External webhook subscribers | #17 |

---

## New Config Variables Summary

| Variable | Purpose | Feature # |
|----------|---------|-----------|
| `RESEND_WEBHOOK_SECRET` | Verify Resend webhook signatures | #2 |
| `HUNTER_API_KEY` | Email verification | #10 |
| `SLACK_WEBHOOK_URL` | Slack notifications | #11 |
| `CORS_ORIGINS` | Strict CORS for production | #24 |
