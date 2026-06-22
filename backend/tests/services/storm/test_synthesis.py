"""Unit tests for STORM section synthesis + refinement.

These tests exercise the citation-validation logic and the bounded
refinement gate without hitting Gemini. Live tests are gated by
``AGENTARY_STORM_LIVE_TEST=1``.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.storm.budget import StormBudget
from app.services.storm.refinement import (
    evaluate_section,
    refine_report_drafts,
)
from app.services.storm.section_synthesizer import (
    SectionDraft,
    ValidatedCitation,
    synthesize_section,
)


def _fake_finding(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "title": "Sample finding",
        "content": "Sample content body that is long enough to matter. " * 3,
        "source_name": "Example.com",
        "source_url": "https://example.com/a",
        "confidence": 0.8,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.fixture
def budget():
    return StormBudget(
        mission_id=str(uuid.uuid4()),
        max_flash_calls=10,
        max_pro_calls=8,
    )


@pytest.mark.asyncio
async def test_synthesize_section_rejects_hallucinated_finding_ids(budget):
    bound = [(_fake_finding(), 0.8), (_fake_finding(), 0.7)]
    allowed_ids = {str(f.id) for (f, _) in bound}
    hallucinated_id = str(uuid.uuid4())

    # First attempt returns one valid + one hallucinated citation → retry
    # Second attempt returns only valid citations.
    valid_id = next(iter(allowed_ids))
    first_response = {
        "content_md": "Body with two claims.",
        "citations": [
            {"finding_id": valid_id, "quote_span": "valid quote", "confidence": 0.9},
            {"finding_id": hallucinated_id, "quote_span": "fake", "confidence": 0.9},
        ],
    }
    second_response = {
        "content_md": "Body with one valid claim.",
        "citations": [
            {"finding_id": valid_id, "quote_span": "valid quote", "confidence": 0.95},
        ],
    }
    call_count = {"n": 0}

    async def fake_gen(*args, **kwargs):
        call_count["n"] += 1
        return first_response if call_count["n"] == 1 else second_response

    with patch(
        "app.services.gemini.generate_structured",
        new=AsyncMock(side_effect=fake_gen),
    ):
        section = {
            "index": 0,
            "title": "Section A",
            "scope": "scope text",
            "expected_evidence_types": ["fact"],
        }
        draft = await synthesize_section(section=section, bound_findings=bound, budget=budget)

    assert draft is not None
    # First attempt had one valid + one hallucinated; partial_evidence true
    # Second attempt accepted with all valid.
    cited_ids = {c.finding_id for c in draft.citations}
    assert hallucinated_id not in cited_ids
    assert valid_id in cited_ids
    assert budget.pro_calls == 2  # one attempt + one retry


def test_evaluate_section_thresholds():
    # Low density — flagged for refinement
    content = "word " * 400  # 400 words, 1 citation → density 0.0025 < 0.005
    citations = [ValidatedCitation(finding_id=str(uuid.uuid4()), quote_span=None, confidence=0.9)]
    bound = [(_fake_finding(), 0.8) for _ in range(5)]
    # Make one finding match the cited id
    citations[0].finding_id = str(bound[0][0].id)

    quality = evaluate_section(
        section_index=0,
        content_md=content,
        citations=citations,
        bound_findings=bound,
    )
    assert quality.verdict == "refine"
    assert any(r.startswith("low_density") for r in quality.reasons)


def test_evaluate_section_drops_when_no_bound_evidence():
    quality = evaluate_section(
        section_index=0,
        content_md="whatever content",
        citations=[],
        bound_findings=[],  # no bound evidence at all
    )
    # reasons: low_density + too_short → but verdict is "drop" because bound_ids is empty
    assert quality.verdict == "drop"


@pytest.mark.asyncio
async def test_refinement_respects_global_cap(budget):
    # Build 3 weak drafts — all would be flagged, but cap is 2
    bound_per_section: dict[int, list] = {}
    drafts: dict[int, SectionDraft] = {}
    for idx in range(3):
        b = [(_fake_finding(), 0.8) for _ in range(5)]
        bound_per_section[idx] = b
        citation = ValidatedCitation(finding_id=str(b[0][0].id), quote_span=None, confidence=0.9)
        drafts[idx] = SectionDraft(
            section_index=idx,
            title=f"Section {idx}",
            content_md="word " * 400,  # low density
            citations=[citation],
            partial_evidence=False,
            refinement_passes=0,
            bound_findings_used=[str(f.id) for (f, _) in b],
        )
    sections = [
        {"index": i, "title": f"s{i}", "scope": "sc", "expected_evidence_types": ["fact"]}
        for i in range(3)
    ]

    refine_mock = AsyncMock(
        side_effect=lambda **kwargs: SectionDraft(
            section_index=kwargs["previous"].section_index,
            title=kwargs["previous"].title,
            content_md="word " * 1500,  # now high density
            citations=kwargs["previous"].citations,
            partial_evidence=False,
            refinement_passes=kwargs["previous"].refinement_passes + 1,
        )
    )
    with patch("app.services.storm.section_synthesizer.refine_section", new=refine_mock):
        updated = await refine_report_drafts(
            drafts=drafts,
            sections=sections,
            bindings=bound_per_section,
            budget=budget,
            max_passes=2,
        )

    refined = sum(1 for d in updated.values() if d.refinement_passes > 0)
    assert refined == 2  # capped at 2 globally


@pytest.mark.asyncio
async def test_refinement_skips_sections_with_no_bound_evidence(budget):
    draft = SectionDraft(
        section_index=0,
        title="orphan",
        content_md="word " * 10,
        citations=[],
        partial_evidence=False,
        refinement_passes=0,
    )
    sections = [{"index": 0, "title": "orphan", "scope": "sc", "expected_evidence_types": []}]
    bindings: dict[int, list] = {0: []}  # no bound findings

    refine_mock = AsyncMock()
    with patch("app.services.storm.section_synthesizer.refine_section", new=refine_mock):
        result = await refine_report_drafts(
            drafts={0: draft},
            sections=sections,
            bindings=bindings,
            budget=budget,
            max_passes=2,
        )

    # No refinement attempted — verdict is "drop", not "refine"
    refine_mock.assert_not_awaited()
    assert result[0].refinement_passes == 0
