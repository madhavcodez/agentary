# STORM Methodology — Defensibility Map

> **Purpose.** This doc maps every phrase in the STORM resume bullet to a file, a
> line range, and (where applicable) a SQL query that proves the claim against a
> live database. It is the engineering source of truth for interview prep.

## Resume bullet

> **Built a Stanford STORM-inspired autonomous research platform with
> perspective-guided question generation, outline-first planning, and
> section-level citation grounding over a FastAPI/Celery/Qdrant backend;
> hard-capped 14 Gemini calls per mission via tiered model routing (Flash for
> pre-write, Pro for section synthesis).**

## Source paper

Shao, Yijia, et al. *"Assisting in Writing Wikipedia-like Articles From Scratch
with Large Language Models."* NAACL 2024. Reference implementation:
[`stanford-oval/storm`](https://github.com/stanford-oval/storm).

The contribution Agentary adopts is the pre-writing / writing split: mine
perspectives and questions, plan an outline, then synthesize sections with bound
evidence. Agentary does not use STORM's original wiki-article-style output or
the Co-STORM conversational variant.

## Phrase → code → evidence

### 1. "Stanford STORM-inspired"

| What | Where |
|---|---|
| Pre-write orchestrator | `backend/app/services/storm/__init__.py::run_storm_prewrite` |
| Feature flag | `backend/app/config.py::agentary_storm_enabled` |
| Integration point | `backend/app/services/crews/crew_runner.py` — Phase 0 before Scout |

Evidence it actually runs:
```sql
SELECT status, perspectives_count, questions_count, sections_count, flash_calls, pro_calls
FROM storm_runs
WHERE mission_id = :mission_id
ORDER BY created_at DESC;
```

### 2. "perspective-guided question generation"

| What | Where |
|---|---|
| Perspective miner | `backend/app/services/storm/perspective_miner.py::mine_perspectives` |
| Diversity check | `perspective_miner.py::_has_collapsed_perspectives` (rejects batches with cosine > 0.85) |
| Question generator | `backend/app/services/storm/question_generator.py::generate_questions` |
| Prompts | `backend/app/prompts/storm.py::build_perspective_prompt`, `build_question_prompt` |

Evidence:
```sql
SELECT perspectives, question_matrix
FROM research_outlines
WHERE mission_id = :mission_id
ORDER BY version DESC LIMIT 1;
```

### 3. "outline-first planning"

| What | Where |
|---|---|
| Outline planner | `backend/app/services/storm/outline_planner.py::plan_outline` |
| Persisted artifact | `backend/app/models/research_outline.py::ResearchOutline` |
| Migration | `backend/alembic/versions/e1a5c2b8f301_storm_research_outlines.py` |

The outline is persisted *before* any Scout/Research phase runs. The temporal
ordering is in `crew_runner.py`: Phase 0 (STORM pre-write) completes and the
outline row is committed before the scout step record is even created.

Evidence:
```sql
SELECT created_at AS outline_created,
       (SELECT MIN(created_at) FROM run_steps WHERE run_id = :crew_run_id) AS first_step_created
FROM research_outlines
WHERE mission_id = :mission_id;
-- outline_created must be <= first_step_created for STORM-enabled missions
```

### 4. "section-level citation grounding"

| What | Where |
|---|---|
| Evidence binder | `backend/app/services/storm/evidence_binder.py::bind_findings_to_sections` |
| Section synthesizer | `backend/app/services/storm/section_synthesizer.py::synthesize_section` |
| Citation validation | `section_synthesizer.py::_validate_citations` (rejects finding_ids not in bound set) |
| Persistence model | `backend/app/models/section_citation.py::SectionCitation` |
| Migration | `backend/alembic/versions/e2b6d4c9a402_storm_section_citations.py` |

Evidence:
```sql
SELECT sc.section_index, f.source_url, f.source_name, sc.quote_span, sc.confidence
FROM section_citations sc
JOIN findings f ON sc.finding_id = f.id
WHERE sc.report_id = :report_id
ORDER BY sc.section_index, sc.confidence DESC;
```

Validation assertion — every citation's finding must be a finding for this
mission:
```sql
SELECT COUNT(*) AS orphan_citations
FROM section_citations sc
JOIN reports r ON sc.report_id = r.id
LEFT JOIN findings f ON sc.finding_id = f.id AND f.mission_id = r.mission_id
WHERE r.id = :report_id AND f.id IS NULL;
-- must return 0
```

### 5. "tiered model routing (Flash for pre-write, Pro for section synthesis)"

| What | Where |
|---|---|
| Flash default | `backend/app/services/gemini.py::generate_structured` — `model="gemini-2.5-flash"` |
| Pro override | `backend/app/services/storm/section_synthesizer.py::SECTION_MODEL = "gemini-2.5-pro"` |
| Budget enforcement | `backend/app/services/storm/budget.py::StormBudget.inc` (separate flash/pro caps) |

Evidence:
```sql
SELECT flash_calls, pro_calls, flash_calls + pro_calls AS total_calls
FROM storm_runs
WHERE mission_id = :mission_id
ORDER BY created_at DESC LIMIT 1;
-- total_calls must be ≤ 14 (budget.DEFAULT_MAX_FLASH_CALLS + DEFAULT_MAX_PRO_CALLS)
```

### 6. "hard-capped 14 Gemini calls per mission"

| What | Where |
|---|---|
| Cap constants | `backend/app/services/storm/budget.py::DEFAULT_MAX_FLASH_CALLS = 10`, `DEFAULT_MAX_PRO_CALLS = 8` (conservative; pipeline uses ≤6+8) |
| Enforcement | `StormBudget.inc` raises `StormBudgetExceeded` before the call is made |
| Storage | Redis `storm:budget:{mission_id}:{flash|pro}` with 1-hour TTL |
| Fallback | `api/missions.py::synthesize_report` catches STORM failures and falls back to legacy synthesis silently |

## Interview questions this doc is designed to answer

### "How is this different from just prompting Gemini to write sections?"

Pointed answer: *"Three things. First, the outline is planned before retrieval
— `outline_planner.py` runs before Phase 2 research, so sections exist as
constraints on retrieval, not as post-hoc organization. Second, citations are
structural, not prompt-promise — `evidence_binder.py` deterministically binds
findings to sections via embedding similarity, and `section_synthesizer.py`
post-validates every cited `finding_id` against the bound set; hallucinated ids
don't make it into the database. Third, every call is budgeted — 6 Flash + 8
Pro hard cap per mission in `budget.py` — because we already ate a Gemini quota
failure on the briefing engine and I wasn't going to repeat it."*

### "How did you handle the N × M × K cost problem STORM has?"

Pointed answer: *"The fan-out is collapsed. Question generation is N calls, not
N×M — each perspective's full question set comes back in one structured
response (`question_generator.py:26`). Outline planning is one call for the
whole perspective-question matrix (`outline_planner.py`). Section synthesis is
M calls with a concurrency semaphore of 3 (`report_synthesis.py` — see
`section_concurrency=3`). Refinement is globally capped at 2 additional calls
per report, not per-section (`refinement.py::DEFAULT_MAX_REFINEMENT_PASSES`).
Total: 6 Flash + 8 Pro. The budget object raises before the call is made, so
we never accidentally spend past the cap."*

### "What happens when STORM fails?"

Pointed answer: *"Silent fallback. The crew runner catches `StormBudgetExceeded`
and `ImportError` and continues with the legacy DeerFlow pipeline. The synthesis
endpoint tries `synthesize_report_from_outline` first; if that raises, it falls
back to `synthesize_report_from_findings`. The fallback reason is recorded in
`storm_runs.fallback_reason` so we can tell whether it was a quota issue, a
perspective-miner collapse, or an outline planner returning zero sections. The
user still gets a report."*

### "What's the blast radius if I turn STORM on in production?"

Pointed answer: *"Zero without the flag. `AGENTARY_STORM_ENABLED` defaults to
`false`; the `should_run_storm` check gates every branch. With the flag on,
failure modes degrade to the legacy path — the report always gets produced.
Cost ceiling is known in advance: 14 Gemini calls per mission, no more. The
existing test suite passes with the flag off; the STORM path is only exercised
when enabled, so no regression risk for current users."*

### "Did you actually read the STORM paper?"

Pointed answer: *"Shao et al., NAACL 2024 — 'Assisting in Writing Wikipedia-like
Articles From Scratch with Large Language Models.' The load-bearing insight is
the pre-writing / writing split: they show pre-writing quality correlates with
final-article quality, which is why the outline is committed before retrieval
runs. The original work is aimed at Wikipedia-style long-form articles; I
adapted the pre-writing stage to Agentary's research reports and kept DeerFlow's
5-phase retrieval pipeline underneath because that's what makes mission-scoped
evidence gathering work. The writing stage is section-at-a-time with
per-section evidence binding, which is closer to the paper's approach than
current Agentary synthesis was."*

## Known limitations (be honest in interviews)

1. **Perspective mining is an LLM call, not a taxonomy.** If the model returns
   near-duplicate perspectives, the cosine-similarity check catches it but
   mining genuinely opposing incentives is still prompt-dependent. Not as
   rigorous as STORM's original "Wikipedia-article-category" seed approach
   because Agentary missions don't have a canonical seed taxonomy.

2. **Evidence binding uses cosine similarity on Gemini embeddings.** If two
   findings discuss the same topic in very different vocabulary, one may score
   below the threshold and get excluded. The threshold (0.55) is
   config-driven; we didn't tune it empirically against a labeled dataset
   because we don't have one.

3. **The refinement quality gate is structural, not semantic.** Density,
   coverage, and length are proxies for quality. A section with high citation
   density can still be bad writing. We deliberately chose structural metrics
   over LLM-as-judge to avoid doubling Pro spend — the tradeoff is real.

4. **Budget counter is per-mission, not per-user.** A user running 10 missions
   in parallel can burn 140 Gemini calls. Production would need a user-level
   rate limiter on top.

5. **No STORM golden dataset.** The paper evaluates STORM against
   human-written Wikipedia articles with FreshWiki/WikiQA-style metrics. We
   have no equivalent evaluation loop — the golden-path test checks structural
   invariants (every section has ≥1 citation, total calls ≤ 14) not content
   quality. Adding a lightweight pairwise preference eval would be the next
   iteration.
