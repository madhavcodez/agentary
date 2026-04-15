"""Unit tests for the permit checklist generator."""
from __future__ import annotations

import pytest

from app.services.permits import (
    PoolSpecs,
    generate_permit_checklist,
    list_supported_jurisdictions,
)


@pytest.fixture
def basic_specs() -> PoolSpecs:
    return PoolSpecs(
        pool_length_ft=32.0,
        pool_width_ft=16.0,
        max_depth_ft=8.0,
        has_spa=False,
        includes_fence_construction=False,
        hoa_applies=False,
    )


def test_plano_tx_jurisdiction_is_supported():
    assert "plano_tx" in list_supported_jurisdictions()


def test_plano_tx_returns_at_least_four_permits(basic_specs: PoolSpecs):
    checklist = generate_permit_checklist("plano_tx", basic_specs)
    assert len(checklist.items) >= 4, checklist.items


def test_plano_tx_includes_pool_barrier_requirement(basic_specs: PoolSpecs):
    checklist = generate_permit_checklist("plano_tx", basic_specs)
    barrier_items = [
        item
        for item in checklist.items
        if "barrier" in item.id or "barrier" in item.name.lower()
    ]
    assert barrier_items, "Pool barrier permit must be present"
    barrier = barrier_items[0]
    assert barrier.statutory_basis is not None
    assert "757" in barrier.statutory_basis, (
        "Barrier permit must cite Texas Health & Safety Code §757"
    )


def test_plano_tx_statutory_notes_mention_chapter_757(basic_specs: PoolSpecs):
    checklist = generate_permit_checklist("plano_tx", basic_specs)
    notes_blob = "\n".join(checklist.statutory_notes)
    assert "757" in notes_blob


def test_plano_tx_has_last_verified_date():
    checklist = generate_permit_checklist("plano_tx")
    assert checklist.last_verified_date, "last_verified_date must be populated"
    assert checklist.last_verified_date.startswith("2026-"), (
        "fixture data should be snapshot-dated in the current year"
    )


def test_plano_tx_spa_addendum_filtered_out_when_no_spa(basic_specs: PoolSpecs):
    checklist = generate_permit_checklist("plano_tx", basic_specs)
    assert not any(item.id == "spa_permit_addendum" for item in checklist.items)


def test_plano_tx_spa_addendum_included_when_spa_present(basic_specs: PoolSpecs):
    specs = basic_specs.model_copy(update={"has_spa": True})
    checklist = generate_permit_checklist("plano_tx", specs)
    assert any(item.id == "spa_permit_addendum" for item in checklist.items)


def test_plano_tx_hoa_permit_toggles_with_hoa_applies(basic_specs: PoolSpecs):
    without = generate_permit_checklist("plano_tx", basic_specs)
    with_hoa = generate_permit_checklist(
        "plano_tx", basic_specs.model_copy(update={"hoa_applies": True})
    )
    without_ids = {item.id for item in without.items}
    with_ids = {item.id for item in with_hoa.items}
    assert "hoa_architectural_review" not in without_ids
    assert "hoa_architectural_review" in with_ids


def test_plano_tx_permits_are_labeled_with_puller(basic_specs: PoolSpecs):
    checklist = generate_permit_checklist("plano_tx", basic_specs)
    for item in checklist.items:
        assert item.puller in {"contractor_typically_pulls", "homeowner_pulls"}


def test_unknown_jurisdiction_raises():
    with pytest.raises(FileNotFoundError):
        generate_permit_checklist("atlantis")


def test_invalid_jurisdiction_slug_raises():
    with pytest.raises(ValueError):
        generate_permit_checklist("../etc/passwd")
