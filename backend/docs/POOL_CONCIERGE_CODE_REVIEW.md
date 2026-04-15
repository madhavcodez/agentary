# Pool Concierge — Code Review Findings (2026-04-15)

Verdict: **RED** — 1 CRITICAL blocks integration test; 8 HIGH; 2 MEDIUM.

## CRITICAL (must fix before any integration test)

| # | File:line | Issue | Fix |
|---|---|---|---|
| 1 | `app/api/verticals/pool_contractors.py:114` | `asyncio.run(...)` inside `BackgroundTask` running in already-running uvicorn event loop → `RuntimeError: This event loop is already running` on every call. Pipeline silently never executes. | Convert `_run_pipeline_sync` to async; register the async coroutine directly via `background_tasks.add_task(run_contractor_pipeline, ...)`. Open a new SessionLocal() inside the coroutine (don't reuse request-scoped session). |

## HIGH (block portfolio polish; some block correctness)

### Stream A
2. `attom.py:35`, `regrid.py:41`, `mapbox_satellite.py:37` — `httpx.AsyncClient` created in `__init__`, never closed. Add `aclose()` + `__aenter__/__aexit__`; callers wrap in `async with` or finally.
3. `mission.py:251` — `cap = max(max_listings * 2, max_listings)` is a no-op (always 2x). Decide intent (strict cap vs buffered) and remove the `max()`.
4. `mission.py:161` — Empty backyard polygon (sqft=0) still passed to placement. Add early return if `backyard_sqft == 0.0`.
5. `pool_listing.py:41` vs `mission.py:183` — `list_price` declared `Integer` but DTO and writes are `float`. Change column to `Float` or `Numeric(12,2)` + companion alembic alteration.

### Stream C
6. `pool_contractors.py:176-186` + `contractor_pipeline.py:223-232` — **ContractorReport created twice**. Endpoint creates row, pipeline creates another. Caller polling the first ID always sees `pending`. Fix: pass `report_id` from endpoint into pipeline; pipeline reuses existing row instead of creating new one.
7. `discovery.py:205` — `asyncio.gather(..., return_exceptions=False)` defeats the belt-and-suspenders intent. Use `return_exceptions=True` + isinstance check.
8. `license_verifier.py:49-50` — `_redis_unavailable` set permanently True on first failure, never resets. Add monotonic backoff retry window (60s).

### Stream D
9. `pool_contracts.py:68-80` — `_load_draft` uses `threading.Lock` inside async path; in-memory store also process-local (multi-worker invisible). Switch to `asyncio.Lock`; document persistence limitation; or move to Redis.
10. `docusign_client.py:98` — `base64.b64decode` of malformed key raises uncaught `binascii.Error` → 500 with traceback. Wrap in try/except, raise `RuntimeError("DocuSign RSA key is not valid base64")`.

## MEDIUM (worth noting)
11. `mission.py:86` — Hardcoded longitude conversion constant (`1/305_000.0`) only correct for ~33°N (Plano TX). OK for v1 demo, document.
12. `pool_contracts.py:141` + `pool_contract_builder.py:239` — `template_key` not validated with `isalnum()` like `checklist.py` does. Already covered by security audit #1.

## Confirmed clean
- TCPA disclosure correctly enforced as RULE 1 in `quote_caller.py:163-198`
- Attorney review default `"PENDING-LEGAL"` propagated through `pool_contract_builder.py:271-272`
- DocuSign hard-blocks send unless `attorney_review_status == "APPROVED"` at `docusign_client.py:180-186`
