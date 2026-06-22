"""Unit tests for STORM pre-writing (perspective miner + question generator + outline planner).

Live Gemini calls are gated behind the ``AGENTARY_STORM_LIVE_TEST=1`` env
var. By default these tests mock ``generate_structured`` so they run
offline and fast.
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.storm.budget import StormBudget, StormBudgetExceeded
from app.services.storm.outline_planner import plan_outline
from app.services.storm.perspective_miner import mine_perspectives
from app.services.storm.question_generator import generate_questions


@pytest.fixture
def fake_mission():
    return SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        name="Evaluate residential solar leases vs. buying in California",
        objective="Identify the cost, risk, and timeline tradeoffs.",
    )


@pytest.fixture
def budget():
    return StormBudget(
        mission_id="11111111-1111-1111-1111-111111111111",
        max_flash_calls=10,
        max_pro_calls=8,
    )


@pytest.mark.asyncio
async def test_perspective_miner_returns_normalised_shape(fake_mission, budget):
    fake_response = {
        "perspectives": [
            {
                "role": "skeptical homeowner",
                "focus": "minimising lifetime cost and contract lock-in",
                "stakes": "20-year exposure if lease terms shift",
                "seed_query": "solar lease vs purchase California total cost",
            },
            {
                "role": "solar installer sales rep",
                "focus": "maximising system adoption with zero-down leases",
                "stakes": "commission on signed leases",
                "seed_query": "zero-down solar lease California benefits",
            },
        ]
    }
    # Also patch the diversity-check embedding path so the test doesn't hit real Gemini.
    with (
        patch(
            "app.services.gemini.generate_structured",
            new=AsyncMock(return_value=fake_response),
        ),
        patch(
            "app.services.storm.perspective_miner._has_collapsed_perspectives",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await mine_perspectives(
            mission=fake_mission, budget=budget, max_perspectives=4
        )

    assert len(result) == 2
    assert result[0]["role"] == "skeptical homeowner"
    assert "focus" in result[0] and "stakes" in result[0] and "seed_query" in result[0]
    assert budget.flash_calls == 1


@pytest.mark.asyncio
async def test_question_generator_clamps_and_validates(fake_mission, budget):
    fake_response = {
        "questions": [
            {"text": "What is the total lifetime cost?", "priority": 0.9, "evidence_type": "fact"},
            {"text": "How does cancellation work?", "priority": 1.5, "evidence_type": "challenge"},
            {"text": "Bad priority", "priority": "not-a-number", "evidence_type": "weird"},
        ]
    }
    with patch("app.services.gemini.generate_structured", new=AsyncMock(return_value=fake_response)):
        result = await generate_questions(
            mission=fake_mission,
            perspective={"role": "skeptical homeowner", "focus": "cost"},
            budget=budget,
            max_questions=5,
        )

    assert len(result) == 3
    assert 0.0 <= result[1]["priority"] <= 1.0  # clamped from 1.5
    assert result[1]["evidence_type"] == "challenge"
    # Unknown evidence type coerced to the "fact" default
    assert result[2]["evidence_type"] == "fact"


@pytest.mark.asyncio
async def test_outline_planner_drops_unknown_question_ids(fake_mission, budget):
    question_matrix = [
        {"id": 0, "perspective_index": 0, "text": "cost?", "priority": 0.9, "evidence_type": "fact"},
        {"id": 1, "perspective_index": 1, "text": "benefits?", "priority": 0.5, "evidence_type": "fact"},
    ]
    fake_response = {
        "title": "Solar lease analysis",
        "sections": [
            {
                "title": "Cost breakdown",
                "scope": "what the 20-year total cost is under each path",
                "source_question_ids": [0, 1, 99],  # 99 doesn't exist
                "expected_evidence_types": ["fact", "comparison", "bogus"],
            }
        ],
    }
    with patch("app.services.gemini.generate_structured", new=AsyncMock(return_value=fake_response)):
        plan = await plan_outline(
            mission=fake_mission,
            perspectives=[{"role": "X", "focus": "y"}] * 2,
            question_matrix=question_matrix,
            budget=budget,
            max_sections=6,
        )

    assert plan is not None
    assert len(plan["sections"]) == 1
    section = plan["sections"][0]
    # 99 dropped, bogus dropped, others kept
    assert section["source_question_ids"] == [0, 1]
    assert "bogus" not in section["expected_evidence_types"]
    assert "fact" in section["expected_evidence_types"]


@pytest.mark.asyncio
async def test_budget_raises_when_cap_hit(fake_mission):
    tight_budget = StormBudget(
        mission_id="22222222-2222-2222-2222-222222222222",
        max_flash_calls=1,
        max_pro_calls=1,
    )
    tight_budget.inc("flash")
    with pytest.raises(StormBudgetExceeded):
        tight_budget.inc("flash")


@pytest.mark.skipif(
    os.environ.get("AGENTARY_STORM_LIVE_TEST") != "1",
    reason="Live Gemini test — enable with AGENTARY_STORM_LIVE_TEST=1",
)
@pytest.mark.asyncio
async def test_live_end_to_end_prewrite(fake_mission):
    """Real Gemini end-to-end sanity — expects valid API key in settings."""
    from app.services.storm.outline_planner import plan_outline
    from app.services.storm.perspective_miner import mine_perspectives
    from app.services.storm.question_generator import generate_questions

    budget = StormBudget(mission_id=str(fake_mission.id))

    perspectives = await mine_perspectives(
        mission=fake_mission, budget=budget, max_perspectives=3
    )
    assert len(perspectives) >= 2

    question_matrix: list[dict] = []
    qid = 0
    for p_idx, p in enumerate(perspectives):
        qs = await generate_questions(
            mission=fake_mission, perspective=p, budget=budget, max_questions=2
        )
        for q in qs:
            question_matrix.append({
                "id": qid,
                "perspective_index": p_idx,
                "text": q["text"],
                "priority": q["priority"],
                "evidence_type": q["evidence_type"],
            })
            qid += 1

    assert len(question_matrix) >= 2

    plan = await plan_outline(
        mission=fake_mission,
        perspectives=perspectives,
        question_matrix=question_matrix,
        budget=budget,
        max_sections=4,
    )
    assert plan is not None and len(plan["sections"]) >= 2
    assert budget.flash_calls <= 6  # budget discipline
