# Pool Concierge — Security Audit Findings (2026-04-15)

Verdict: **YELLOW** — 2 must-fix before demo with real PII; 11 follow-ups.

## Must-fix before demo (2 HIGH)

| # | File:line | Issue | Fix |
|---|---|---|---|
| 1 | `app/services/contracts/pool_contract_builder.py:236-239` | `template_key` not validated → path traversal to arbitrary YAML/template files on disk | Add allowlist `{"tx_pool_installation_v1"}` at API layer + reuse `isalnum()+underscore` guard from `permits/checklist.py:70`. CRITICAL on Linux deployments. |
| 2 | `app/api/verticals/pool_contracts.py:77 (_load_draft)` | IDOR — any authenticated user can fetch any draft by ID; PII (buyer name, phone, address, full PDF) leaks across users | Scope `_drafts` dict by `(draft_id, user_id)`; assert `draft.owner_user_id == current_user.id` in `_load_draft`, return 403 on mismatch. |

## Important follow-ups (11 HIGH)

### Stream C (voice / contractors)
3. `quote_caller.py:469-477` — `notes=f"config_build_failed: {exc}"` echoes raw exception to API caller. Use opaque string + log server-side.
4. `quote_caller.py:503-505` — same pattern with `notes=str(exc)` from voice pipeline.
5. `quote_caller.py:463-485` — TCPA disclosure relies on adapter honoring `live_config["system_prompt"]`. Add an assertion that outgoing `system_instruction` starts with `build_disclosure_preamble()`.
6. `discovery.py` — `zipcode` from request body has no regex validator. Add `r"^\d{5}(-\d{4})?$"` to `ContractorKickoffRequest`.
7. `license_verifier.py:190` — Add `follow_redirects=False` to `httpx.AsyncClient` for TDLR call.

### Stream D (contracts / permits)
8. `pool_contract_builder.py:68-72` — Jinja2 autoescape only matches `.html`; `.md.j2` template is unescaped → stored XSS via buyer name in `markdown_preview`/`html` API field. Set `autoescape=True` globally or strip Jinja control chars in DTO.
9. `pool_contract_builder.py:173-196` — `title` from metadata YAML embedded into raw HTML `<title>`. Wrap with `html.escape(title)`.
10. `pool_contracts.py:281-286` — `markdown_preview` returned in API response → if logged at DEBUG = full PII contract leak. Move preview behind separate authenticated endpoint or strip from default response.
11. `docusign_client.py:98` — RSA private key bytes may surface in `jose` traceback. Wrap `_build_jwt_assertion` in try/except, raise sanitised `RuntimeError("DocuSign JWT build failed")`.
12. `pool_contracts.py:338-350` — `envelope_id` URL param not validated against the draft → user can poll any DocuSign envelope status in account. Verify ownership + match against draft-stored envelope_id.

### Settings
13. `config.py:13` — `database_url` default `"postgresql://agentary:agentary@localhost:5432/agentary"` has hardcoded creds. Add validator like `jwt_secret_key` to reject defaults.
14. `config.py:14` — `redis_url` no auth/TLS by default. Validate non-dev environments require auth.

## Confirmed clean
- TCPA disclosure wiring (caveat: adapter assertion missing — see #5)
- DocuSign triple-gate at `docusign_client.py:180-200` ✅
- `permits/checklist.py:70` path traversal guard ✅
- Thread-safe `_drafts` lock ✅
- No real secrets in defaults
- `yaml.safe_load` used throughout
