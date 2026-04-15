"""End-to-end integration test for the Pool Concierge vertical.

Covers the full Stream A → Stream E flow:

1. A fixture user + saved search for Plano TX 75024
2. All external services are mocked (Zillow, ATTOM, Regrid, Mapbox,
   Yelp, Google Places, TDLR, Twilio/Pipecat, DocuSign)
3. ``run_full_pool_pipeline`` runs against an in-memory ``FakeSession``
4. Assertions:
   (a) :class:`PoolPipelineRun` reaches ``ready`` status
   (b) ≥1 :class:`PoolListing` persisted with ``score>0``
   (c) ≥1 :class:`ContractorReport` with a verified contractor
   (d) :class:`ContractDraft` generated with
       ``attorney_review_status == "PENDING-LEGAL"``
   (e) The Telegram digest contains all 3 listings + preview URLs
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.models.contractor_report import ContractorReport
from app.models.mission import Mission
from app.models.pool_listing import PoolListing
from app.models.pool_pipeline_run import (
    PoolPipelineRun,
    PoolPipelineRunStatus,
)
from app.models.pool_saved_search import PoolSavedSearch
from app.models.project import Project
from app.services.contractors.discovery import ContractorCandidate
from app.services.contractors.license_verifier import LicenseStatus
from app.services.contractors.quote_caller import (
    PoolSpecs as CallerPoolSpecs,
    QuoteResult,
)
from app.services.contracts.dto import (
    BuyerInfo,
    ContractDraft,
    ContractorInfo,
    PaymentMilestone,
    Quote,
)
from app.services.data_sources.base_connector import SourceResult
from app.services.permits.checklist import generate_permit_checklist
from app.services.telegram.pool_handlers import (
    build_digest_buttons,
    render_digest,
)
from app.verticals.pool_concierge.contractor_pipeline import (
    run_contractor_pipeline,
)
from app.verticals.pool_concierge.mission import run_pool_concierge_mission
from app.verticals.pool_concierge.orchestrator import (
    run_full_pool_pipeline,
)


# ---------------------------------------------------------------------------
# FakeSession (copied locally so this test is self-contained)
# ---------------------------------------------------------------------------


class FakeSession:
    """Minimum session surface the orchestrator + Stream C expect."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.flushed = 0
        self.committed = 0
        self.rolled_back = 0

    def _ensure_id(self, obj: Any) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid4()

    def add(self, obj: Any) -> None:
        self._ensure_id(obj)
        self.added.append(obj)

    def flush(self) -> None:
        for obj in self.added:
            self._ensure_id(obj)
        self.flushed += 1

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def query(self, model: type) -> "_FakeQuery":
        rows = [o for o in self.added if isinstance(o, model)]
        return _FakeQuery(rows)


class _FakeQuery:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def filter(self, *_c: Any) -> "_FakeQuery":
        return self

    def one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None


# ---------------------------------------------------------------------------
# Fixtures — user, saved search, external service fakes
# ---------------------------------------------------------------------------


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def saved_search(user_id: UUID) -> PoolSavedSearch:
    return PoolSavedSearch(
        id=uuid4(),
        user_id=user_id,
        zipcode="75024",
        radius_mi=5.0,
        max_budget=1_200_000,
        min_budget=500_000,
        enabled=True,
    )


# --- mission-level fakes (Zillow/ATTOM/Regrid/Mapbox) ---------------------


class _FakeZillow:
    name = "Zillow"
    provider = "zillow"
    description = ""

    async def search(self, query: str, **_: Any) -> SourceResult:
        data = [
            {
                "zpid": "z-1",
                "address": "2025 Legacy Dr, Plano, TX 75024",
                "price": 1_100_000,
                "url": "https://zillow.com/2",
            },
            {
                "zpid": "z-2",
                "address": "1001 Independence Pkwy, Plano, TX 75075",
                "price": 850_000,
                "url": "https://zillow.com/1",
            },
            {
                "zpid": "z-3",
                "address": "700 Tiny Ct, Plano, TX 75023",
                "price": 520_000,
                "url": "https://zillow.com/3",
            },
        ]
        return SourceResult(
            data=data,
            raw_response=None,
            total_results=len(data),
            source_name=self.name,
        )


class _FakeAttom:
    name = "ATTOM"
    _DETAIL_BY_ADDRESS = {
        "Legacy": {
            "lot_size_sqft": 18_000.0,
            "building_footprint_sqft": 3_000.0,
        },
        "Independence": {
            "lot_size_sqft": 12_000.0,
            "building_footprint_sqft": 2_200.0,
        },
        "Tiny": {
            "lot_size_sqft": 4_500.0,
            "building_footprint_sqft": 1_800.0,
        },
    }

    async def get_property_detail(self, address: str) -> SourceResult:
        key = "Tiny"
        if "Legacy" in address:
            key = "Legacy"
        elif "Independence" in address:
            key = "Independence"
        return SourceResult(
            data=[self._DETAIL_BY_ADDRESS[key]],
            raw_response=None,
            total_results=1,
            source_name=self.name,
        )


class _FakeRegrid:
    name = "Regrid"

    async def get_parcel_polygon(self, address: str) -> SourceResult:
        if "Legacy" in address:
            w, d = 90.0, 200.0
        elif "Independence" in address:
            w, d = 80.0, 150.0
        else:
            w, d = 50.0, 90.0
        cx, cy = -96.70, 33.02
        dlon = (w / 2.0) / 305_000.0
        dlat = (d / 2.0) / 364_000.0
        polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [cx - dlon, cy - dlat],
                    [cx + dlon, cy - dlat],
                    [cx + dlon, cy + dlat],
                    [cx - dlon, cy + dlat],
                    [cx - dlon, cy - dlat],
                ]
            ],
        }
        return SourceResult(
            data=[{"polygon": polygon}],
            raw_response=None,
            total_results=1,
            source_name=self.name,
        )


class _FakeMapbox:
    name = "Mapbox Satellite"

    async def get_aerial_image(
        self,
        bbox: tuple[float, float, float, float],
        *,
        zoom: int = 20,
        size: tuple[int, int] = (1024, 1024),
    ) -> SourceResult:
        return SourceResult(
            data=[{"image_bytes": b"PNG", "format": "png"}],
            raw_response=None,
            total_results=1,
            source_name=self.name,
            source_url="https://mock.mapbox/tile.png",
            metadata={"bbox": list(bbox), "zoom": zoom},
        )


# --- contractor-pipeline fakes (Yelp/Google Places/TDLR/Twilio) -----------


def _fake_discover_pool_contractors():
    async def _impl(
        zipcode: str,
        radius_mi: float = 15.0,
        min_rating: float = 4.0,
        min_reviews: int = 20,
        limit: int = 10,
    ) -> list[ContractorCandidate]:
        return [
            ContractorCandidate(
                name="BlueWave Pools",
                phone="+1-214-555-0101",
                address="",
                rating=4.8,
                reviews_count=200,
                source="yelp",
                business_url="",
                raw_payload={},
            ),
            ContractorCandidate(
                name="Reef Pools",
                phone="+1-214-555-0103",
                address="",
                rating=4.7,
                reviews_count=140,
                source="google_places",
                business_url="",
                raw_payload={},
            ),
            ContractorCandidate(
                name="Ghost Pools",  # intentionally fails TDLR verification
                phone="+1-214-555-0104",
                address="",
                rating=4.3,
                reviews_count=30,
                source="google_places",
                business_url="",
                raw_payload={},
            ),
        ]

    return _impl


def _fake_verify_license():
    async def _impl(
        state: str, business_name: str, city: str | None = None
    ) -> LicenseStatus:
        if business_name == "Ghost Pools":
            return LicenseStatus(found=False, status="no_records")
        return LicenseStatus(
            found=True,
            license_number=f"APS-{hash(business_name) & 0xffff:04x}",
            status="Active",
        )

    return _impl


def _fake_request_quote_via_voice():
    async def _impl(
        contractor: ContractorCandidate,
        listing: Any,
        pool_specs: CallerPoolSpecs,
        max_call_duration_sec: int = 240,
    ) -> QuoteResult:
        if contractor.name == "BlueWave Pools":
            return QuoteResult(
                contractor_name="BlueWave Pools",
                contractor_phone=contractor.phone,
                status="ok",
                price_low_usd=60_000,
                price_high_usd=80_000,
                eta_weeks=8,
                rating=contractor.rating,
            )
        return QuoteResult(
            contractor_name=contractor.name,
            contractor_phone=contractor.phone,
            status="ok",
            price_low_usd=70_000,
            price_high_usd=90_000,
            eta_weeks=10,
            rating=contractor.rating,
        )

    return _impl


# --- Injection wrappers ---------------------------------------------------


def _mission_with_fakes():
    async def _impl(
        zipcode: str,
        radius_mi: float = 5.0,
        max_listings: int = 10,
        db: Any | None = None,
    ) -> Any:
        return await run_pool_concierge_mission(
            zipcode=zipcode,
            radius_mi=radius_mi,
            max_listings=max_listings,
            db=db,
            zillow=_FakeZillow(),
            attom=_FakeAttom(),
            regrid=_FakeRegrid(),
            mapbox=_FakeMapbox(),
        )

    return _impl


def _contractor_with_fakes():
    async def _impl(listing: PoolListing, db: Any, **kwargs: Any) -> Any:
        return await run_contractor_pipeline(
            listing=listing,
            db=db,
            discover_fn=_fake_discover_pool_contractors(),
            verify_fn=_fake_verify_license(),
            quote_fn=_fake_request_quote_via_voice(),
            commit=False,
        )

    return _impl


def _permit_with_real_data():
    def _impl(jurisdiction: str, specs: Any) -> Any:
        return generate_permit_checklist(
            jurisdiction=jurisdiction, pool_specs=specs
        )

    return _impl


# ---------------------------------------------------------------------------
# Contract fakes (DocuSign is NOT hit — build_pool_contract is pure)
# ---------------------------------------------------------------------------


def _build_buyer() -> BuyerInfo:
    return BuyerInfo(
        full_name="Madhav Test",
        email="buyer@example.com",
        phone="+1-214-555-9999",
        billing_address="1 Buyer Ln, Plano, TX 75024",
        installation_address="2025 Legacy Dr, Plano, TX 75024",
    )


def _build_contractor() -> ContractorInfo:
    return ContractorInfo(
        company_name="BlueWave Pools",
        license_number="APS-1234",
        contact_name="Alex Contractor",
        email="alex@bluewave.test",
        phone="+1-214-555-0101",
        business_address="5 Wave Dr, Plano, TX 75024",
    )


def _build_quote() -> Quote:
    return Quote(
        quote_id="q-1",
        pool_length_ft=40.0,
        pool_width_ft=20.0,
        shallow_end_depth_ft=3.5,
        deep_end_depth_ft=6.5,
        pool_shape="rectangular",
        included_equipment=("pump", "filter", "saltwater_system"),
        total_price_usd=70_000.0,
        start_date=date(2026, 6, 1),
        substantial_completion_date=date(2026, 9, 15),
        warranty_years=2,
        payment_schedule=(
            PaymentMilestone(
                name="Deposit",
                description="On signing",
                percent=20.0,
                amount_usd=14_000.0,
            ),
            PaymentMilestone(
                name="Rough-in",
                description="After excavation",
                percent=40.0,
                amount_usd=28_000.0,
            ),
            PaymentMilestone(
                name="Final",
                description="On substantial completion",
                percent=40.0,
                amount_usd=28_000.0,
            ),
        ),
    )


@dataclass
class _StubListingForContract:
    address: str = "2025 Legacy Dr, Plano, TX 75024"


# ---------------------------------------------------------------------------
# The test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pool_concierge_e2e_golden_path(
    user_id: UUID, saved_search: PoolSavedSearch
) -> None:
    # Given a saved search for Plano TX 75024
    assert saved_search.zipcode == "75024"
    assert saved_search.enabled is True

    session = FakeSession()

    # When we run the full pipeline (all externals mocked)
    result = await run_full_pool_pipeline(
        user_id=user_id,
        zipcode=saved_search.zipcode,
        radius_mi=saved_search.radius_mi,
        db=session,  # type: ignore[arg-type]
        max_listings=10,
        top_n=3,
        mission_fn=_mission_with_fakes(),
        contractor_fn=_contractor_with_fakes(),
        permit_fn=_permit_with_real_data(),
    )

    # (a) PoolPipelineRun reaches 'ready' status
    run_rows = [o for o in session.added if isinstance(o, PoolPipelineRun)]
    assert len(run_rows) == 1
    assert run_rows[0].status == PoolPipelineRunStatus.ready
    assert result.status == PoolPipelineRunStatus.ready.value

    # (b) ≥1 PoolListing persisted with score>0
    listings = [o for o in session.added if isinstance(o, PoolListing)]
    assert len(listings) >= 1
    assert all(l.score > 0 for l in listings)

    # Supporting structure: Mission + Project also created.
    assert any(isinstance(o, Mission) for o in session.added)
    assert any(isinstance(o, Project) for o in session.added)

    # (c) ≥1 ContractorReport with a verified contractor.
    reports = [o for o in session.added if isinstance(o, ContractorReport)]
    assert len(reports) >= 1
    assert any(r.verified_count >= 1 for r in reports)

    # (d) ContractDraft generated with PENDING-LEGAL attorney review.
    # Mock the PDF renderer — we only need to confirm the builder's
    # gating flag flows through unchanged. Real PDF generation is
    # covered by Stream D's own tests.
    from unittest.mock import patch

    from app.services.contracts import pool_contract_builder as pcb_mod

    mock_pdf = pcb_mod._PdfResult(
        pdf_bytes=b"%PDF-1.4 mock", renderer="mock"
    )
    with patch.object(pcb_mod, "_html_to_pdf", return_value=mock_pdf):
        draft: ContractDraft = pcb_mod.build_pool_contract(
            buyer=_build_buyer(),
            contractor=_build_contractor(),
            listing=_StubListingForContract(),
            quote=_build_quote(),
            template_key="tx_pool_installation_v1",
        )
    assert draft.attorney_review_status == "PENDING-LEGAL"
    assert draft.pdf_bytes  # non-empty

    # (e) Telegram digest contains all 3 listings with preview URLs.
    digest_text = render_digest(
        {
            "run_id": str(run_rows[0].id),
            "zipcode": saved_search.zipcode,
            "status": "ready",
            "summary": run_rows[0].summary,
        }
    )
    assert "2025 Legacy Dr" in digest_text or "Legacy" in digest_text
    assert digest_text.count("/pool/listing/") >= 3

    buttons = build_digest_buttons(
        {
            "summary": run_rows[0].summary,
        }
    )
    assert len(buttons) == 3
    prefixes_per_row = [
        {btn.callback_data[:3] for btn in row} for row in buttons
    ]
    for s in prefixes_per_row:
        assert s == {"pq:", "pc:", "pp:"}


@pytest.mark.asyncio
async def test_pool_concierge_e2e_records_correct_counts(
    user_id: UUID, saved_search: PoolSavedSearch
) -> None:
    """Total listings counted from mission, ready_listings from contractor."""
    session = FakeSession()
    result = await run_full_pool_pipeline(
        user_id=user_id,
        zipcode=saved_search.zipcode,
        radius_mi=saved_search.radius_mi,
        db=session,  # type: ignore[arg-type]
        max_listings=10,
        top_n=3,
        mission_fn=_mission_with_fakes(),
        contractor_fn=_contractor_with_fakes(),
        permit_fn=_permit_with_real_data(),
    )
    # At least 2 of 3 Plano listings scored (big lots pass the threshold).
    assert result.total_listings >= 1
    # Every listing that made it into the top-3 should be ready.
    assert result.ready_listings == len(result.listings)
