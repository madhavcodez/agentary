"""Perspective miner — STORM pre-writing step 1.

Discovers diverse stakeholder viewpoints on the mission topic. Perspectives
are NOT the same as expert agents (``app.services.crews.expert_registry``):
experts are tool-wielding researchers, while perspectives are stakeholder
lenses (skeptical regulator, beneficiary, insider, outsider, etc.) that
drive the question matrix in the next step.

Diversity is enforced structurally: if the miner returns perspectives whose
focus-sentence embeddings are too similar to each other, the batch is
rejected and the call is retried once with a stronger "emphasize contrast"
prompt. This prevents silent collapse onto near-duplicates.
"""

from __future__ import annotations

import logging
from typing import Any

from ...prompts.storm import (
    PERSPECTIVE_SCHEMA_HINT,
    build_perspective_prompt,
)
from .budget import StormBudget

logger = logging.getLogger(__name__)

# Two perspectives are considered duplicates when their focus-sentence
# embeddings have cosine similarity above this threshold.
_DUPLICATE_COSINE_THRESHOLD = 0.85
# Minimum viable perspective count — below this we abandon and fall back.
_MIN_PERSPECTIVES = 2


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def _has_collapsed_perspectives(
    perspectives: list[dict[str, Any]],
) -> bool:
    """True when any pair of perspective focus-sentences is >0.85 cosine."""
    from ..gemini import embed_text

    if len(perspectives) < 2:
        return False

    embeddings: list[list[float]] = []
    for p in perspectives:
        focus = p.get("focus") or p.get("role") or ""
        if not focus.strip():
            continue
        try:
            emb = await embed_text(focus, task_type="SEMANTIC_SIMILARITY")
        except Exception as exc:  # pragma: no cover — best-effort
            logger.debug("perspective_miner: embed failed, skipping diversity check (%s)", exc)
            return False
        embeddings.append(emb)

    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            if _cosine(embeddings[i], embeddings[j]) > _DUPLICATE_COSINE_THRESHOLD:
                return True
    return False


async def mine_perspectives(
    *,
    mission: Any,
    budget: StormBudget,
    max_perspectives: int,
) -> list[dict[str, Any]]:
    """Return a list of ``{role, focus, stakes, seed_query}`` perspectives.

    Makes one Flash call (two if the first output has collapsed perspectives).
    Raises :class:`StormBudgetExceeded` via ``budget.inc("flash")`` if the
    cap has already been hit.
    """
    from ..gemini import generate_structured

    prompt = build_perspective_prompt(
        mission_name=mission.name,
        objective=getattr(mission, "objective", None),
        max_perspectives=max_perspectives,
    )

    budget.inc("flash")
    try:
        result = await generate_structured(prompt, schema_hint=PERSPECTIVE_SCHEMA_HINT)
    except Exception as exc:
        logger.warning("perspective_miner: initial call failed for mission %s: %s", mission.id, exc)
        return []

    perspectives = _normalise(result.get("perspectives"), max_perspectives)

    if len(perspectives) < _MIN_PERSPECTIVES:
        logger.warning(
            "perspective_miner: only %d usable perspectives, below minimum",
            len(perspectives),
        )
        return perspectives  # caller decides whether to abort

    if await _has_collapsed_perspectives(perspectives):
        logger.info(
            "perspective_miner: retrying once — diversity threshold breached for mission %s",
            mission.id,
        )
        retry_prompt = prompt + (
            "\n\nCRITICAL: Your previous attempt produced perspectives that were "
            "too similar. Emphasize genuine contrast — different incentives, "
            "different information environments, different success criteria."
        )
        try:
            budget.inc("flash")
            retry_result = await generate_structured(
                retry_prompt, schema_hint=PERSPECTIVE_SCHEMA_HINT
            )
            retry_perspectives = _normalise(retry_result.get("perspectives"), max_perspectives)
            if len(
                retry_perspectives
            ) >= _MIN_PERSPECTIVES and not await _has_collapsed_perspectives(retry_perspectives):
                return retry_perspectives
        except Exception as exc:
            logger.warning("perspective_miner: retry failed (%s)", exc)

    return perspectives


def _normalise(raw: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw[:limit]:
        if not isinstance(item, dict):
            continue
        role = (item.get("role") or "").strip()
        focus = (item.get("focus") or "").strip()
        if not role or not focus:
            continue
        out.append(
            {
                "role": role[:200],
                "focus": focus[:500],
                "stakes": (item.get("stakes") or "").strip()[:500],
                "seed_query": (item.get("seed_query") or "").strip()[:500],
            }
        )
    return out
