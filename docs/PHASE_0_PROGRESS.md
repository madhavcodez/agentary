# Phase 0 — Foundation & Domain Restructure Progress

## Status: IN PROGRESS

### Checklist

- [ ] Step 1: Explore and Inventory → docs/RENAME_MAP.md
- [ ] Step 2: Create new directory structure
- [ ] Step 3: Create ALL database models (20+)
- [ ] Step 4: Create ALL Pydantic schemas
- [ ] Step 5: Create core infrastructure (events, celery, telemetry, flags)
- [ ] Step 6: Create API route stubs
- [ ] Step 7: Remove old domain code (archive to _archive/)
- [ ] Step 8: Create Alembic migration
- [ ] Step 9: Seed data script
- [ ] Step 10: Docker & infra updates
- [ ] Step 11: Frontend restructure
- [ ] Step 12: Tests & validation

### Success Criteria

- [ ] Zero "SecretAIRY" references in runtime code
- [ ] ALL 20+ new model files created with complete definitions
- [ ] ALL Pydantic schemas created
- [ ] ALL API route stubs created and registered
- [ ] Alembic migration runs cleanly
- [ ] core/events.py, core/telemetry.py, core/feature_flags.py exist and work
- [ ] tasks/celery_app.py configured
- [ ] Seed script creates default ExpertAgents, Workflows, Sources
- [ ] Frontend restructured with new nav and stub pages
- [ ] Docker Compose starts with Celery worker + beat
- [ ] docs/PHASE_0_PROGRESS.md tracks completion
