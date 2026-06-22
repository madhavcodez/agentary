"""Bind findings to outline sections using embedding similarity.

Pure function — no LLM call. For each outline section, compute the cosine
similarity between the section scope embedding and each finding's content
embedding. Keep the top-K findings per section with score above the
configured threshold.

A finding may appear in multiple sections if it satisfies the threshold
for each; the section synthesizer cites the bound subset, so duplication
is acceptable and sometimes desirable.

When a section binds zero findings the binder returns it with an empty
list rather than silently dropping it — the refinement loop treats that
as a signal to either request more research or skip the section rather
than let the section synthesizer hallucinate citations.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_K_PER_SECTION = 5
DEFAULT_SCORE_THRESHOLD = 0.55


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def _embed_scope(scope: str) -> list[float]:
    from ..gemini import embed_text
    return await embed_text(scope, task_type="SEMANTIC_SIMILARITY")


async def _embed_finding_content(finding: Any) -> list[float]:
    from ..gemini import embed_text
    snippet = (finding.title or "") + "\n" + (finding.content or "")
    return await embed_text(snippet[:2000], task_type="RETRIEVAL_DOCUMENT")


async def bind_findings_to_sections(
    *,
    sections: Sequence[dict[str, Any]],
    findings: Iterable[Any],
    k_per_section: int = DEFAULT_K_PER_SECTION,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> dict[int, list[tuple[Any, float]]]:
    """Return ``{section_index: [(finding, score), ...]}``.

    Embeds each section scope once and each finding once, then computes
    pairwise cosine similarity in-memory. For the typical Agentary mission
    (≤50 findings × ≤6 sections) this is 300 cosine ops — trivial.
    """
    findings_list = list(findings)
    if not sections or not findings_list:
        return {}

    # Embed every finding once
    finding_embeddings: list[tuple[Any, list[float]]] = []
    for f in findings_list:
        try:
            emb = await _embed_finding_content(f)
        except Exception as exc:
            logger.debug("evidence_binder: finding embed failed for %s: %s", f.id, exc)
            continue
        finding_embeddings.append((f, emb))

    bindings: dict[int, list[tuple[Any, float]]] = {}
    for section in sections:
        idx = int(section.get("index", 0))
        scope = section.get("scope") or section.get("title") or ""
        try:
            scope_emb = await _embed_scope(scope)
        except Exception as exc:
            logger.warning(
                "evidence_binder: scope embed failed for section %d: %s", idx, exc
            )
            bindings[idx] = []
            continue

        scored: list[tuple[Any, float]] = []
        for finding, finding_emb in finding_embeddings:
            score = _cosine(scope_emb, finding_emb)
            if score >= score_threshold:
                scored.append((finding, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        bindings[idx] = scored[:k_per_section]

    total_bound = sum(len(v) for v in bindings.values())
    empty_sections = [i for i, v in bindings.items() if not v]
    logger.info(
        "evidence_binder: bound %d findings across %d sections (%d empty — flagged for refinement or skip)",
        total_bound,
        len(sections),
        len(empty_sections),
    )
    return bindings
