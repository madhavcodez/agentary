# Rename Map — SecretAIRY → Agentary

## Domain Rename Table

| Old Term | New Term | Action |
|----------|----------|--------|
| SecretAIRY / secretairy | Agentary / agentary | Rename everywhere |
| Opportunity (job listing) | REMOVED | No equivalent |
| Match / match_engine | REMOVED | Replaced by expert scoring |
| Dossier / dossier_gen | Report / report_gen | Rename |
| Profile (resume) | KnowledgeBase | Rename |
| CallCampaign | VoiceExtraction | Rename |
| Autopilot / autopilot.py | MissionRunner / mission_runner.py | Rename |
| Scout / scout.py | LiveFeed / live_feed.py | Rename |
| Pipeline / pipeline_engine | REMOVED | No sales pipeline |
| outreach_gen | REMOVED | No cold outreach |

## Files to Archive (→ _archive/)

### Models
- backend/app/models/opportunity.py
- backend/app/models/match.py
- backend/app/models/pipeline.py
- backend/app/models/dossier.py
- backend/app/models/profile.py (Skill, Experience, Preference)
- backend/app/models/email_event.py
- backend/app/models/email_suppression.py

### Schemas
- backend/app/schemas/opportunity.py
- backend/app/schemas/match.py
- backend/app/schemas/pipeline.py
- backend/app/schemas/dossier.py
- backend/app/schemas/profile.py

### API Routes
- backend/app/api/scout.py
- backend/app/api/opportunities.py
- backend/app/api/matches.py
- backend/app/api/dossiers.py
- backend/app/api/autopilot.py
- backend/app/api/ingest.py
- backend/app/api/profile.py

### Services
- backend/app/services/match_engine.py
- backend/app/services/pipeline_engine.py
- backend/app/services/outreach_gen.py
- backend/app/services/dossier_gen.py
- backend/app/services/autopilot.py
- backend/app/services/profile_builder.py
- backend/app/services/call_script_gen.py
- backend/app/services/ingest/ (entire directory)

### Tests
- backend/tests/test_greenhouse.py
- backend/tests/test_match_engine.py
- backend/tests/test_profile_builder.py
- backend/tests/test_call_script_gen.py

### Frontend Pages
- dashboard/app/scout/
- dashboard/app/jobs/
- dashboard/app/opportunities/
- dashboard/app/matches/
- dashboard/app/outreach/
- dashboard/app/profile/

### Frontend Components
- dashboard/components/ProfileForm.tsx
- dashboard/components/OpportunityCard.tsx
- dashboard/components/MatchCard.tsx
- dashboard/components/ScoreBadge.tsx
- dashboard/components/DossierView.tsx
- dashboard/components/scout/ (entire directory)
- dashboard/components/outreach/ (entire directory)

### Frontend Lib
- dashboard/lib/hooks/useOutreachData.ts
- dashboard/lib/hooks/useScoutWebSocket.ts

## Files to Keep (with renaming)
- backend/app/models/user.py — keep as-is
- backend/app/models/contact.py — keep as-is
- backend/app/models/call_campaign.py — rename to voice_extraction (but archive, new model created)
- backend/app/models/call_log.py — archive, replaced by CallRecord in voice_extraction
- backend/app/models/research.py — archive, replaced by Finding
- backend/app/models/action_log.py — archive, replaced by AuditLog
- backend/app/models/policy.py — keep as-is for now
- backend/app/services/twilio_client.py — keep (used by voice)
- backend/app/services/email_sender.py — keep
- backend/app/services/qdrant_store.py — keep
- backend/app/services/gemini.py — keep
- backend/app/services/circuit_breakers.py — keep
- backend/app/services/scheduler.py — keep
- backend/app/services/research/ — keep (gemini_search, exa_search, engine)
- backend/app/voice/ — keep entire directory
- backend/app/auth.py — keep
- backend/app/config.py — update (rename secretairy refs)
- backend/app/database.py — keep
- backend/app/deps.py — keep
- backend/app/main.py — rewrite router registrations
- backend/app/api/auth.py — keep
- backend/app/api/health.py — keep
- backend/app/api/contacts.py — keep
- backend/app/api/campaigns.py — archive (replaced by voice routes)
- backend/app/api/research.py — keep (will be updated)
- backend/app/api/analytics.py — keep (will be updated)
- backend/app/api/policies.py — keep
- backend/app/api/webhooks.py — keep
