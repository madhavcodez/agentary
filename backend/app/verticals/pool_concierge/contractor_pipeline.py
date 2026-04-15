"""End-to-end contractor pipeline for a :class:`PoolListing`.

Steps:

1. Discover contractors near the listing's ZIP (Yelp + Google Places).
2. Verify licenses in parallel (``asyncio.gather``, semaphore=3).
3. Call the top N verified contractors for voice quotes in parallel
   (semaphore=2 — be polite to small businesses).
4. Rank returned quotes and persist a :class:`ContractorReport` row.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.contractor_report import ContractorReport, ContractorReportStatus
from ...models.pool_listing import PoolListing
from ...services.contractors.discovery import (
    ContractorCandidate,
    discover_pool_contractors,
)
from ...services.contractors.license_verifier import (
    LicenseStatus,
    verify_license,
)
from ...services.contractors.quote_caller import (
    PoolSpecs,
    QuoteResult,
    request_quote_via_voice,
)
from ...services.contractors.quote_ranker import RankedQuote, rank_quotes

logger = logging.getLogger(__name__)

_LICENSE_CONCURRENCY = 3
_QUOTE_CONCURRENCY = 2
_QUOTE_CALL_CAP = 5  # top-N verified contractors to actually call
_ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")


@dataclass(frozen=True)
class ContractorReportDTO:
    """In-memory view of the pipeline result (also returned by API)."""

    report_id: UUID
    pool_listing_id: UUID
    status: str
    discovery_count: int
    verified_count: int
    quote_count: int
    top_quotes: list[RankedQuote] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "report_id": str(self.report_id),
            "pool_listing_id": str(self.pool_listing_id),
            "status": self.status,
            "discovery_count": self.discovery_count,
            "verified_count": self.verified_count,
            "quote_count": self.quote_count,
            "top_quotes": [rq.to_jsonable() for rq in self.top_quotes],
        }


# ---------------------------------------------------------------------------
# Dependency injection points (for tests)
# ---------------------------------------------------------------------------


class _DiscoveryFn(Protocol):
    async def __call__(
        self,
        zipcode: str,
        radius_mi: float = ...,
        min_rating: float = ...,
        min_reviews: int = ...,
        limit: int = ...,
    ) -> list[ContractorCandidate]: ...


class _VerifyFn(Protocol):
    async def __call__(
        self,
        state: str,
        business_name: str,
        city: str | None = None,
    ) -> LicenseStatus: ...


class _QuoteFn(Protocol):
    async def __call__(
        self,
        contractor: ContractorCandidate,
        listing: PoolListing,
        pool_specs: PoolSpecs,
        max_call_duration_sec: int = ...,
    ) -> QuoteResult: ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_zip(address: str | None) -> str | None:
    """Pull a US 5-digit ZIP out of a free-form address."""
    if not address:
        return None
    match = _ZIP_RE.search(address)
    return match.group(1) if match else None


def _extract_state(address: str | None) -> str:
    """Cheap state detector — default TX for Stream C v1 (Plano)."""
    if not address:
        return "TX"
    # Look for ", XX" two-letter state codes.
    match = re.search(r",\s*([A-Z]{2})\s+\d{5}", address)
    if match:
        return match.group(1).upper()
    return "TX"


def _extract_city(address: str | None) -> str | None:
    """Grab the city component from ``..., City, ST ZIP``."""
    if not address:
        return None
    parts = [p.strip() for p in address.split(",")]
    if len(parts) < 3:
        return None
    # ``<street>, <city>, <ST ZIP>``
    return parts[-2] or None


def _pool_specs_from_listing(listing: PoolListing) -> PoolSpecs:
    """Build :class:`PoolSpecs` from a listing's placement + polygon."""
    placement = listing.pool_placement or {}
    backyard = float(listing.backyard_sqft or 0.0)
    return PoolSpecs.from_placement(
        placement, backyard_sqft=backyard
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


async def _verify_all(
    candidates: list[ContractorCandidate],
    state: str,
    city: str | None,
    verify_fn: _VerifyFn,
) -> list[tuple[ContractorCandidate, LicenseStatus]]:
    """Verify every candidate in parallel under a concurrency cap."""
    sem = asyncio.Semaphore(_LICENSE_CONCURRENCY)

    async def _one(
        cand: ContractorCandidate,
    ) -> tuple[ContractorCandidate, LicenseStatus]:
        async with sem:
            status = await verify_fn(
                state=state, business_name=cand.name, city=city
            )
            return cand, status

    return list(await asyncio.gather(*(_one(c) for c in candidates)))


async def _quote_all(
    verified: list[ContractorCandidate],
    listing: PoolListing,
    pool_specs: PoolSpecs,
    quote_fn: _QuoteFn,
) -> list[QuoteResult]:
    """Place quote calls in parallel under a (small) concurrency cap."""
    sem = asyncio.Semaphore(_QUOTE_CONCURRENCY)

    async def _one(cand: ContractorCandidate) -> QuoteResult:
        async with sem:
            return await quote_fn(
                contractor=cand,
                listing=listing,
                pool_specs=pool_specs,
            )

    return list(await asyncio.gather(*(_one(c) for c in verified)))


async def run_contractor_pipeline(
    listing: PoolListing,
    db: Session,
    *,
    radius_mi: float = 15.0,
    min_rating: float = 4.0,
    min_reviews: int = 20,
    discovery_limit: int = 10,
    discover_fn: _DiscoveryFn | None = None,
    verify_fn: _VerifyFn | None = None,
    quote_fn: _QuoteFn | None = None,
    commit: bool = True,
    existing_report_id: UUID | None = None,
) -> ContractorReportDTO:
    """Run discovery -> verify -> quote -> rank, persist report.

    Audit fix (code-review HIGH #6): when ``existing_report_id`` is
    provided the pipeline looks up the existing ``ContractorReport`` row
    rather than creating a new one. This closes the double-insert bug
    where the API endpoint created a placeholder row for the caller to
    poll, and the pipeline then created a second row the caller never
    learned about.

    Injection points (``discover_fn`` / ``verify_fn`` / ``quote_fn``)
    let tests stub the whole pipeline without patching modules.
    """
    disc = discover_fn or discover_pool_contractors
    ver = verify_fn or verify_license
    quot = quote_fn or request_quote_via_voice

    zipcode = _extract_zip(listing.address)
    state = _extract_state(listing.address)
    city = _extract_city(listing.address)

    if existing_report_id is not None:
        report = (
            db.query(ContractorReport)
            .filter(ContractorReport.id == existing_report_id)
            .one_or_none()
        )
        if report is None:
            raise ValueError(
                f"existing_report_id {existing_report_id} not found"
            )
    else:
        report = ContractorReport(
            pool_listing_id=listing.id,
            status=ContractorReportStatus.pending,
            discovery_count=0,
            verified_count=0,
            quote_count=0,
            top_quotes=[],
        )
        db.add(report)
        db.flush()

    if not zipcode:
        logger.warning(
            "Listing %s has no parseable ZIP; skipping contractor pipeline",
            listing.id,
        )
        report.status = ContractorReportStatus.failed
        report.completed_at = datetime.now(timezone.utc)
        if commit:
            db.commit()
        return ContractorReportDTO(
            report_id=report.id,
            pool_listing_id=listing.id,
            status=report.status.value,
            discovery_count=0,
            verified_count=0,
            quote_count=0,
            top_quotes=[],
        )

    try:
        candidates = await disc(
            zipcode=zipcode,
            radius_mi=radius_mi,
            min_rating=min_rating,
            min_reviews=min_reviews,
            limit=discovery_limit,
        )
    except Exception:
        logger.exception("Contractor discovery failed for %s", listing.id)
        report.status = ContractorReportStatus.failed
        report.completed_at = datetime.now(timezone.utc)
        if commit:
            db.commit()
        return ContractorReportDTO(
            report_id=report.id,
            pool_listing_id=listing.id,
            status=report.status.value,
            discovery_count=0,
            verified_count=0,
            quote_count=0,
            top_quotes=[],
        )

    report.discovery_count = len(candidates)

    verification_results = await _verify_all(candidates, state, city, ver)
    verified_candidates = [
        cand for cand, status in verification_results if status.found
    ]
    report.verified_count = len(verified_candidates)

    to_call = verified_candidates[:_QUOTE_CALL_CAP]

    report.status = ContractorReportStatus.quoting
    db.flush()

    pool_specs = _pool_specs_from_listing(listing)

    quotes = await _quote_all(to_call, listing, pool_specs, quot)
    ok_quotes = [q for q in quotes if q.status == "ok"]
    report.quote_count = len(ok_quotes)

    ranked = rank_quotes(quotes)

    report.top_quotes = [rq.to_jsonable() for rq in ranked]
    if ranked:
        report.status = ContractorReportStatus.ready
    else:
        report.status = ContractorReportStatus.failed
    report.completed_at = datetime.now(timezone.utc)

    if commit:
        db.commit()
    else:
        db.flush()

    return ContractorReportDTO(
        report_id=report.id,
        pool_listing_id=listing.id,
        status=report.status.value,
        discovery_count=report.discovery_count,
        verified_count=report.verified_count,
        quote_count=report.quote_count,
        top_quotes=ranked,
    )
