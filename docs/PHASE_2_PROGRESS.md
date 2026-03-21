# Phase 2: Voice Extraction System — Progress

## Status: COMPLETE

## Summary
Built a generalized voice extraction system on top of the existing Pipecat + Gemini Live + Twilio pipeline. The system transforms the "call recruiters" infrastructure into a configurable "call anyone about anything" platform.

## Success Criteria Checklist

- [x] VoiceExtraction and CallRecord models with migration (010b)
- [x] Finding model extended with call_record_id FK
- [x] CallScriptGenerator produces context-aware scripts via Gemini
- [x] ExtractionService extracts structured data from transcripts
- [x] VoicePipelineAdapter bridges to Pipecat/Twilio (or simulates)
- [x] Batch calling (plan N calls, execute sequentially)
- [x] Post-call processing generates Findings
- [x] 6 built-in extraction templates (Business Info, Pricing, Availability, Screening, Survey, Custom)
- [x] API routes for sessions, templates, batches
- [x] Twilio webhook handlers (status, recording, transcription)
- [x] Frontend: extraction list + detail with transcript + extraction display
- [x] voice_caller tool in CrewRunner tool registry
- [x] Simulation mode when Twilio not configured
- [x] Celery tasks (execute_voice_call, process_completed_call, execute_voice_batch)
- [x] docs/PHASE_2_PROGRESS.md updated

## Architecture

### Models
- `VoiceExtraction` — Campaign/batch parent with persona, extraction schema, targets
- `CallRecord` — Individual call with transcript, extracted data, confidence
- `Finding` — Extended with `call_record_id` FK for voice-sourced findings

### Services (backend/app/services/voice/)
- `voice_service.py` — Orchestrator: create, plan, start, process, batch
- `call_script_generator.py` — AI script generation via Gemini
- `extraction_service.py` — Structured data extraction from transcripts
- `transcript_processor.py` — Transcript cleanup, analysis, summarization
- `voice_pipeline_adapter.py` — Twilio bridge + simulation mode
- `templates.py` — 6 built-in extraction templates

### API Routes
- `/voice/sessions` — CRUD + call management
- `/voice/templates` — Built-in template listing
- `/voice/batch` — Batch planning and execution
- `/webhooks/twilio/voice-*` — Status, recording, transcription webhooks

### Tool Registry
- `voice_caller` tool in `services/crews/tools/voice_caller.py`
- Accepts: phone_number, business_name, questions, context
- Returns: extracted_data, transcript_summary, confidence

### Celery Tasks
- `voice.execute_call` — Single call execution
- `voice.process_completed` — Post-call extraction + findings
- `voice.execute_batch` — Sequential batch execution

## Key Design Decisions

1. **VoiceExtraction + CallRecord** (not VoiceSession): Aligns with Agent 0's domain model refactoring. VoiceExtraction is the campaign parent, CallRecord is per-call.
2. **Simulation mode**: When Twilio isn't configured, Gemini generates synthetic transcripts so the full pipeline works during development.
3. **Template-based**: 6 built-in templates provide pre-configured extraction schemas that users can clone.
4. **Finding integration**: Voice-extracted data creates proper Finding objects linked to projects/missions.

## Files Created/Modified

### New Files
- `backend/app/models/voice_extraction.py`
- `backend/app/services/voice/voice_service.py`
- `backend/app/services/voice/call_script_generator.py`
- `backend/app/services/voice/extraction_service.py`
- `backend/app/services/voice/transcript_processor.py`
- `backend/app/services/voice/voice_pipeline_adapter.py`
- `backend/app/services/voice/templates.py`
- `backend/app/schemas/voice.py`
- `backend/app/api/voice_sessions.py`
- `backend/app/api/voice_templates.py`
- `backend/app/api/voice_batch.py`
- `backend/app/api/voice_webhooks.py`
- `backend/alembic/versions/010b_voice_extraction.py`
- `backend/tests/test_voice_extraction.py`
- `dashboard/app/voice/extractions/page.tsx`
- `dashboard/app/voice/extractions/[id]/page.tsx`

### Modified Files
- `backend/app/models/finding.py` — Added call_record_id FK
- `backend/app/models/__init__.py` — Added VoiceExtraction, CallRecord imports
- `backend/app/main.py` — Registered voice extraction routers
- `backend/app/tasks/voice_tasks.py` — Real Celery task implementations
- `backend/app/services/crews/tools/voice_caller.py` — Real implementation
- `backend/requirements.txt` — Added celery[redis]
