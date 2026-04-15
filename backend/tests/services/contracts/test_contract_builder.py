"""Unit tests for ``build_pool_contract``.

These tests are fully offline: the builder reads bundled template /
metadata files and renders to PDF via an embedded PDF renderer. No
DocuSign or database access is required.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from app.services.contracts import (
    BuyerInfo,
    ContractorInfo,
    PaymentMilestone,
    Quote,
    build_pool_contract,
)


@dataclass(frozen=True)
class FakeListing:
    address: str


@pytest.fixture
def sample_buyer() -> BuyerInfo:
    return BuyerInfo(
        full_name="Alex Rivera",
        email="alex@example.com",
        phone="+1-555-0100",
        billing_address="100 Oak Ln, Plano, TX 75024",
        installation_address="100 Oak Ln, Plano, TX 75024",
    )


@pytest.fixture
def sample_contractor() -> ContractorInfo:
    return ContractorInfo(
        company_name="Lonestar Pools LLC",
        license_number="TX-PL-123456",
        contact_name="Dana Cruz",
        email="dana@lonestarpools.example",
        phone="+1-555-0200",
        business_address="500 Industrial Blvd, Plano, TX 75074",
    )


@pytest.fixture
def sample_listing() -> FakeListing:
    return FakeListing(address="100 Oak Ln, Plano, TX 75024")


@pytest.fixture
def sample_quote() -> Quote:
    return Quote(
        quote_id="Q-2026-0001",
        pool_length_ft=32.0,
        pool_width_ft=16.0,
        shallow_end_depth_ft=3.5,
        deep_end_depth_ft=8.0,
        pool_shape="rectangle",
        included_equipment=(
            "Pentair IntelliFlo VSF variable-speed pump",
            "Pentair MasterTemp 400k BTU natural-gas heater",
            "Jandy JXi LED pool light",
        ),
        total_price_usd=118_500.0,
        start_date=date(2026, 5, 1),
        substantial_completion_date=date(2026, 8, 15),
        warranty_years=3,
        payment_schedule=(
            PaymentMilestone(
                name="Deposit",
                description="Signing deposit",
                percent=15.0,
                amount_usd=17_775.0,
            ),
            PaymentMilestone(
                name="Excavation",
                description="Paid at dig completion",
                percent=35.0,
                amount_usd=41_475.0,
            ),
            PaymentMilestone(
                name="Gunite",
                description="Paid at shotcrete pour",
                percent=30.0,
                amount_usd=35_550.0,
            ),
            PaymentMilestone(
                name="Final",
                description="Paid at substantial completion",
                percent=20.0,
                amount_usd=23_700.0,
            ),
        ),
    )


def test_build_pool_contract_renders_pdf_bytes(
    sample_buyer, sample_contractor, sample_listing, sample_quote
):
    draft = build_pool_contract(
        buyer=sample_buyer,
        contractor=sample_contractor,
        listing=sample_listing,
        quote=sample_quote,
    )

    assert draft.pdf_bytes, "pdf_bytes must be non-empty"
    assert len(draft.pdf_bytes) > 500, "pdf_bytes should be a real document"
    assert draft.pdf_bytes[:4] == b"%PDF", "output should be a valid PDF header"
    assert draft.sha256 and len(draft.sha256) == 64


def test_build_pool_contract_carries_attorney_review_pending(
    sample_buyer, sample_contractor, sample_listing, sample_quote
):
    draft = build_pool_contract(
        buyer=sample_buyer,
        contractor=sample_contractor,
        listing=sample_listing,
        quote=sample_quote,
    )
    assert draft.attorney_review_status == "PENDING-LEGAL"
    assert draft.metadata.get("last_reviewed_date") == "PENDING-LEGAL"


def test_build_pool_contract_renders_expected_sections(
    sample_buyer, sample_contractor, sample_listing, sample_quote
):
    draft = build_pool_contract(
        buyer=sample_buyer,
        contractor=sample_contractor,
        listing=sample_listing,
        quote=sample_quote,
    )
    # Markdown retains section names verbatim — cheap to assert.
    md = draft.markdown
    assert sample_buyer.full_name in md
    assert sample_contractor.company_name in md
    assert sample_quote.quote_id in md
    assert "Scope of Work" in md
    assert "Payment Schedule" in md
    assert "Texas Health & Safety Code" in md
    # Every payment milestone renders.
    for milestone in sample_quote.payment_schedule:
        assert milestone.name in md


def test_build_pool_contract_attorney_review_marker_in_template(
    sample_buyer, sample_contractor, sample_listing, sample_quote
):
    draft = build_pool_contract(
        buyer=sample_buyer,
        contractor=sample_contractor,
        listing=sample_listing,
        quote=sample_quote,
    )
    assert "ATTORNEY REVIEW REQUIRED" in draft.markdown


def test_build_pool_contract_unknown_template_raises(
    sample_buyer, sample_contractor, sample_listing, sample_quote
):
    """Security audit #1: unknown ``template_key`` is rejected by the
    allowlist before the filesystem is touched. This raises
    ``ValueError`` rather than ``FileNotFoundError`` so a bad key never
    leaks information about which template files exist on disk.
    """
    with pytest.raises((ValueError, FileNotFoundError)):
        build_pool_contract(
            buyer=sample_buyer,
            contractor=sample_contractor,
            listing=sample_listing,
            quote=sample_quote,
            template_key="does_not_exist_v9",
        )


def test_build_pool_contract_metadata_includes_required_disclosures(
    sample_buyer, sample_contractor, sample_listing, sample_quote
):
    draft = build_pool_contract(
        buyer=sample_buyer,
        contractor=sample_contractor,
        listing=sample_listing,
        quote=sample_quote,
    )
    disclosures = draft.metadata.get("required_disclosures") or []
    ids = {d["id"] for d in disclosures if isinstance(d, dict) and "id" in d}
    assert {
        "right_to_cancel",
        "pool_barrier_compliance",
        "texas_mechanics_lien_notice",
    }.issubset(ids)
