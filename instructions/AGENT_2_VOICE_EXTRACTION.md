# AGENT 2 — Voice Extraction System

## YOUR MISSION

You are a coding agent. Build the **voice extraction system** — expert agents make phone calls to businesses/people, have natural conversations, and extract structured data. Generalize the existing Pipecat + Gemini Live + Twilio pipeline from "call recruiters" to "call anyone about anything."

**Start:** `/plan Read this entire file, explore existing voice code (Pipecat, Gemini Live, Twilio), then build everything.`

---

## WHAT YOU'RE BUILDING

The existing codebase has a **working voice pipeline**: Pipecat + Gemini Live + Twilio Media Streams. Your job:
1. **Generalize** from job-search calls to any research extraction call
2. **Make configurable** per mission — different questions, personas, extraction goals
3. **Build extraction pipeline** — after each call, AI extracts structured data from transcript
4. **Make orchestratable** — Agent 1's CrewRunner triggers calls as part of research
5. **Build pre-call planning** — AI determines who to call, what to ask
6. **Build post-call processing** — transcript analysis, data extraction, finding generation

### Example: "Research gas station prices near downtown Austin"
```
1. Pre-call: Google Places finds 12 gas stations with phone numbers
2. Plan: Call list with questions (regular price, premium, diesel, hours)
3. Call: "Hi, I'm doing a price survey. What's your current price for regular?"
4. Extract: {station: "Shell 6th St", regular: 3.29, premium: 3.89, diesel: null}
5. Repeat for all stations
6. Post-process: Compile prices, identify cheapest, calculate averages
7. Generate Findings for the mission
```

---

## MODELS

### voice_session.py
Fields: id (UUID PK), mission_id (FK missions nullable), crew_task_id (FK crew_tasks nullable), user_id (FK users), session_type (str: research_extraction|screening|survey|custom), status (str: planned|queued|in_progress|connected|completed|failed|no_answer|voicemail), target_name (str), target_phone (str), target_business (str nullable), target_context (JSONB — everything known about target), persona_config (JSONB: name, role, tone, style), extraction_goals (JSONB — array of {field, question, type, required}), call_script (Text — AI-generated conversation guide), system_prompt (Text — for Gemini Live during call), twilio_call_sid (str nullable), recording_url (Text nullable), transcript (Text nullable), transcript_segments (JSONB — [{speaker, text, timestamp}]), duration_seconds (Float), outcome (str: data_extracted|partial_data|no_data|wrong_number|voicemail|refused|error), extracted_data (JSONB — structured data from call), extraction_confidence (Float), cost_usd (Float), started_at, connected_at, completed_at, created_at, updated_at.

### extraction_template.py
Fields: id (UUID PK), user_id (FK users nullable), name (str), description (Text), category (str: business_info|pricing|availability|hours|services|opinions|screening|custom), extraction_fields (JSONB — [{field_name, field_type, question_template, required, validation}]), persona_template (JSONB), is_system (Bool), is_active (Bool), created_at, updated_at.

---

## SERVICES

### voice_service.py
- `create_session(data, db)` → VoiceSession
- `plan_calls_for_task(crew_task, targets, extraction_goals, db)` → list[VoiceSession] — given targets from Google Places/web research, create planned sessions with AI-generated scripts
- `start_session(session_id, db)` → initiate Twilio call, set up Pipecat pipeline
- `get_session_status(session_id, db)` → real-time status
- `process_completed_call(session_id, db)` → run extraction, generate findings

### call_script_generator.py
Use Gemini to generate per-target: opening line, prioritized questions, follow-up probes, objection handlers, closing, and the complete system_prompt for Gemini Live during the call. The script adapts to what we know about the target (business type, context).

### extraction_service.py
- `extract_from_transcript(session, db)` → Given transcript + extraction_goals, use Gemini to extract structured data. For each field: extracted value, confidence, transcript reference. Validate types/ranges. Return overall quality score.
- `extract_findings(session, extraction_result, db)` → Convert extractions to Finding objects.

### transcript_processor.py
- `process_transcript(raw, segments)` → Speaker diarization, ASR cleanup, key moment identification, talk ratio, sentiment.
- `summarize_call(transcript, context)` → Concise summary.

### voice_pipeline_adapter.py
Bridge to existing Pipecat + Twilio:
- `create_outbound_call(session)` → Start call via Twilio, return call_sid
- `setup_media_stream(call_sid, session)` → Configure Twilio MediaStream → Pipecat → Gemini Live
- `build_gemini_live_config(session)` → Dynamic system prompt with target context + extraction goals

**SIMULATION MODE**: If Twilio isn't configured, use Gemini to generate a synthetic transcript based on target info. This lets the full pipeline work during development without real calls.

---

## BUILT-IN EXTRACTION TEMPLATES (6)

1. **Business Info** — hours, address, services, contact person, website
2. **Pricing** — prices for specific products/services, bulk discounts
3. **Availability** — appointment slots, inventory, wait times
4. **Screening** — qualify against criteria (tenant, vendor, candidate)
5. **Survey** — opinion questions with recording
6. **Custom** — user defines all fields

---

## API ROUTES

**`/api/voice/sessions`**: POST / (create), GET / (list, filter by mission/status), GET /{id} (detail with transcript + extraction), POST /{id}/start (initiate call), POST /{id}/stop, GET /{id}/transcript, GET /{id}/extraction, POST /{id}/reextract.

**`/api/voice/templates`**: GET / (list), POST / (create custom), GET /{id}.

**`/api/voice/batch`**: POST / (batch of calls — plan N calls), GET /{batch_id} (status), GET /{batch_id}/results (aggregated).

**Webhooks**: POST /api/webhooks/twilio/status, POST /api/webhooks/twilio/recording, POST /api/webhooks/twilio/transcription.

---

## CELERY TASKS

```python
@celery_app.task(name="voice.execute_call", queue="voice")
def execute_voice_call(session_id: str): ...

@celery_app.task(name="voice.process_completed", queue="voice")
def process_completed_call(session_id: str): ...

@celery_app.task(name="voice.execute_batch", queue="voice")
def execute_voice_batch(session_ids: list[str]): ...  # Sequential with delays
```

---

## FRONTEND

### Voice Session Detail (`/projects/[id]/voice/[sessionId]`)
- Call info: target, phone, status, duration
- Live transcript (if in progress) — real-time text
- Completed transcript with speaker labels + timestamps
- Extracted Data panel — key-value pairs with confidence badges
- Recording player (if available)
- Findings generated from this call

### Voice Batch View (`/projects/[id]/voice`)
- Table of all sessions for project
- Batch progress (4/12 calls completed)
- Aggregated extracted data across calls
- Export as CSV/JSON

---

## INTEGRATION WITH CREW RUNNER

Register `voice_caller` tool in Agent 1's tool registry:
- Accepts: phone_number, business_name, questions, context
- Creates VoiceSession with extraction goals
- Generates call script
- Executes or queues call
- Returns: extracted_data, transcript_summary, confidence

---

## SUCCESS CRITERIA (Agent 7 Checks)

- [ ] VoiceSession and ExtractionTemplate models with migrations
- [ ] CallScriptGenerator produces context-aware scripts via Gemini
- [ ] ExtractionService extracts structured data from transcripts
- [ ] VoicePipelineAdapter bridges to Pipecat/Twilio (or simulates)
- [ ] Batch calling (plan N calls, execute sequentially)
- [ ] Post-call processing generates Findings
- [ ] 6 built-in extraction templates
- [ ] API routes for sessions, templates, batches
- [ ] Twilio webhook handlers
- [ ] Frontend: session detail with transcript + extraction
- [ ] voice_caller tool in tool registry for CrewRunner
- [ ] Simulation mode when Twilio not configured
- [ ] Celery tasks
- [ ] docs/PHASE_2_PROGRESS.md updated
