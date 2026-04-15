"""FastAPI router for pool-contract and permit endpoints (Stream D).

This router is intentionally additive. Wire it in ``app/main.py`` with:

    from .api.verticals.pool_contracts import router as pool_contracts_router
    app.include_router(pool_contracts_router)

Endpoints
---------
POST /api/verticals/pool/contracts/draft
    Render a pool installation contract draft from buyer + quote data.

POST /api/verticals/pool/contracts/{draft_id}/send
    Send a drafted contract to DocuSign. Requires ``force=true`` AND an
    approved attorney_review_status AND live DocuSign credentials.
    Otherwise returns a mock envelope id and logs a warning.

GET /api/verticals/pool/permits/{jurisdiction}
    Return the static permit checklist for a jurisdiction.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass, replace as dataclass_replace
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ...deps import get_current_user, get_db
from ...models.user import User
from ...services.contracts import (
    BuyerInfo,
    ContractDraft,
    ContractorInfo,
    PaymentMilestone,
    Quote,
    build_pool_contract,
)
from ...services.contracts.docusign_client import (
    EnvelopeStatus,
    Signer,
    create_envelope,
    get_envelope_status,
)
from ...services.permits import (
    PermitChecklist,
    PoolSpecs,
    generate_permit_checklist,
    list_supported_jurisdictions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verticals/pool", tags=["pool-concierge"])


# ---------------------------------------------------------------------------
# In-memory draft store
# ---------------------------------------------------------------------------
# Contracts are ephemeral here — a production build would persist them in
# a dedicated ``contract_drafts`` table, but the task is scoped to avoid
# adding new ORM models. The store is process-local.
#
# Audit fixes:
#   * security #2 — IDOR: the store is now keyed by ``(draft_id,
#     owner_user_id)``. ``_load_draft`` requires the caller's user_id;
#     mismatches return 404 (not 403) to avoid leaking existence.
#   * code-review #9 — switch from ``threading.Lock`` to
#     ``asyncio.Lock`` because every caller is on the event loop.
#     Documented persistence limitation: process-local, multi-worker
#     invisible; a production deployment should move this to Redis.
#   * code-review #10 / security #20 — wrap the draft with the stored
#     ``envelope_id`` after send so we can enforce an ownership check
#     when the caller polls envelope status.


@dataclass(frozen=True)
class ContractDraftRecord:
    """Per-user draft entry with bookkeeping for send/envelope flow.

    ``draft`` is the rendered contract; ``owner_user_id`` scopes access
    (security audit #2); ``envelope_id`` is populated once the draft is
    sent so the envelope-status endpoint can cross-check ownership.
    """

    draft: ContractDraft
    owner_user_id: str
    envelope_id: str | None = None


_drafts: dict[tuple[str, str], ContractDraftRecord] = {}
_drafts_lock = asyncio.Lock()


async def _store_draft(draft: ContractDraft, user_id: str) -> None:
    record = ContractDraftRecord(draft=draft, owner_user_id=user_id)
    async with _drafts_lock:
        _drafts[(draft.draft_id, user_id)] = record


async def _load_draft(draft_id: str, user_id: str) -> ContractDraftRecord:
    """Load a draft scoped to ``user_id``.

    Returns 404 on mismatch (rather than 403) to avoid confirming the
    existence of a draft the caller does not own (security audit #2).
    """
    async with _drafts_lock:
        record = _drafts.get((draft_id, user_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Contract draft not found")
    return record


async def _update_envelope(draft_id: str, user_id: str, envelope_id: str) -> None:
    """Persist ``envelope_id`` against the stored draft record."""
    async with _drafts_lock:
        existing = _drafts.get((draft_id, user_id))
        if existing is None:
            return
        _drafts[(draft_id, user_id)] = dataclass_replace(
            existing, envelope_id=envelope_id
        )


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PaymentMilestoneIn(_Frozen):
    name: str
    description: str
    percent: float = Field(ge=0.0, le=100.0)
    amount_usd: float = Field(ge=0.0)


class QuoteIn(_Frozen):
    quote_id: str
    pool_length_ft: float = Field(gt=0.0)
    pool_width_ft: float = Field(gt=0.0)
    shallow_end_depth_ft: float = Field(gt=0.0)
    deep_end_depth_ft: float = Field(gt=0.0)
    pool_shape: str
    included_equipment: list[str]
    total_price_usd: float = Field(ge=0.0)
    start_date: date
    substantial_completion_date: date
    warranty_years: int = Field(ge=0)
    payment_schedule: list[PaymentMilestoneIn]


class BuyerIn(_Frozen):
    full_name: str
    email: str
    phone: str
    billing_address: str
    installation_address: str


class ContractorIn(_Frozen):
    company_name: str
    license_number: str
    contact_name: str
    email: str
    phone: str
    business_address: str


class DraftContractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buyer_id: UUID
    listing_id: UUID
    quote_id: str
    buyer: BuyerIn
    contractor: ContractorIn
    quote: QuoteIn
    template_key: str = "tx_pool_installation_v1"


class ContractDraftResponse(BaseModel):
    """Default draft response.

    Security audit #10: ``markdown_preview`` is deliberately NOT included
    in the default response. It contains the full rendered contract
    (full PII: buyer name, phone, address). Any client that logs or
    caches API responses at DEBUG would leak every buyer's PII. Callers
    that explicitly want the preview fetch it via
    ``GET /contracts/{draft_id}/preview``.
    """

    model_config = ConfigDict(extra="forbid")

    draft_id: str
    template_key: str
    attorney_review_status: str
    sha256: str
    renderer: str
    pdf_base64: str
    pdf_url: str
    metadata: dict[str, Any]


class ContractDraftPreviewResponse(BaseModel):
    """Preview-only response exposed via a dedicated endpoint."""

    model_config = ConfigDict(extra="forbid")

    draft_id: str
    markdown_preview: str


class SignerIn(_Frozen):
    email: str
    name: str
    role: str
    routing_order: int = 1


class SendContractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signers: list[SignerIn]


class SendContractResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str
    envelope_id: str
    is_mock: bool
    attorney_review_status: str
    force: bool


class EnvelopeStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    envelope_id: str
    status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_dto_quote(q: QuoteIn) -> Quote:
    return Quote(
        quote_id=q.quote_id,
        pool_length_ft=q.pool_length_ft,
        pool_width_ft=q.pool_width_ft,
        shallow_end_depth_ft=q.shallow_end_depth_ft,
        deep_end_depth_ft=q.deep_end_depth_ft,
        pool_shape=q.pool_shape,
        included_equipment=tuple(q.included_equipment),
        total_price_usd=q.total_price_usd,
        start_date=q.start_date,
        substantial_completion_date=q.substantial_completion_date,
        warranty_years=q.warranty_years,
        payment_schedule=tuple(
            PaymentMilestone(
                name=m.name,
                description=m.description,
                percent=m.percent,
                amount_usd=m.amount_usd,
            )
            for m in q.payment_schedule
        ),
    )


def _listing_view_from_db(db: Session, listing_id: UUID) -> Any:
    """Resolve the listing row. Falls back to a stub if PoolListing is missing.

    Stream A owns the PoolListing model. If the row is not found or the
    import fails (Stream A not yet merged), we return an object with the
    minimum shape expected by the builder (an ``address`` attr). The API
    surfaces a 404 when a listing_id is supplied but not resolvable.
    """
    try:
        from ...models.pool_listing import PoolListing  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        logger.warning("PoolListing model unavailable; using stub")

        class _Stub:
            address = "UNKNOWN-ADDRESS (PoolListing model not available)"

        return _Stub()

    row = db.query(PoolListing).filter(PoolListing.id == listing_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Pool listing not found")
    return row


def _draft_to_response(draft: ContractDraft) -> ContractDraftResponse:
    """Render a ``ContractDraft`` for API return.

    Security audit #10: ``markdown_preview`` is intentionally omitted.
    """
    return ContractDraftResponse(
        draft_id=draft.draft_id,
        template_key=draft.template_key,
        attorney_review_status=draft.attorney_review_status,
        sha256=draft.sha256,
        renderer=str(draft.metadata.get("renderer", "unknown")),
        pdf_base64=base64.b64encode(draft.pdf_bytes).decode("ascii"),
        pdf_url=f"/api/verticals/pool/contracts/{draft.draft_id}/pdf",
        metadata=dict(draft.metadata),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/contracts/draft", response_model=ContractDraftResponse, status_code=201)
async def draft_pool_contract(
    body: DraftContractRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContractDraftResponse:
    """Render a pool installation contract to PDF.

    The response includes a base64 PDF and a signed URL for download.
    ``attorney_review_status`` is carried through from the template;
    the send endpoint refuses to proceed unless it is ``APPROVED``.

    Audit fix (security #2): the draft is stored scoped to the caller's
    ``user.id`` so no other authenticated user can fetch it.
    """
    listing = _listing_view_from_db(db, body.listing_id)
    buyer = BuyerInfo(**body.buyer.model_dump())
    contractor = ContractorInfo(**body.contractor.model_dump())
    quote = _to_dto_quote(body.quote)

    draft = build_pool_contract(
        buyer=buyer,
        contractor=contractor,
        listing=listing,
        quote=quote,
        template_key=body.template_key,
    )
    await _store_draft(draft, str(user.id))
    logger.info(
        "Drafted pool contract %s for user %s (review=%s)",
        draft.draft_id,
        user.id,
        draft.attorney_review_status,
    )
    return _draft_to_response(draft)


@router.get(
    "/contracts/{draft_id}/preview",
    response_model=ContractDraftPreviewResponse,
)
async def preview_pool_contract(
    draft_id: str,
    user: User = Depends(get_current_user),
) -> ContractDraftPreviewResponse:
    """Return the markdown preview of a drafted contract.

    Audit fix (security #10): moved out of the default draft response so
    PII-heavy preview is not accidentally captured in generic API logs.
    Scoped to ``user.id`` (security audit #2).
    """
    record = await _load_draft(draft_id, str(user.id))
    return ContractDraftPreviewResponse(
        draft_id=record.draft.draft_id,
        markdown_preview=record.draft.markdown,
    )


@router.post(
    "/contracts/{draft_id}/send",
    response_model=SendContractResponse,
    status_code=202,
)
async def send_pool_contract(
    draft_id: str,
    body: SendContractRequest,
    force: bool = Query(
        default=False,
        description="Must be true to actually send to DocuSign. Safety gate.",
    ),
    user: User = Depends(get_current_user),
) -> SendContractResponse:
    """Send a drafted contract to DocuSign.

    Safety layers:
    1. ``force=true`` must be supplied in the query string.
    2. ``attorney_review_status`` on the draft must be ``APPROVED``.
    3. DocuSign credentials must be configured.

    Any missing layer => mock envelope + warning log.

    Audit fix (security #2 / #20): draft is scoped by ``user.id`` and
    the returned ``envelope_id`` is persisted back onto the record so
    the envelope-status endpoint can verify ownership.
    """
    record = await _load_draft(draft_id, str(user.id))
    draft = record.draft
    if not body.signers:
        raise HTTPException(status_code=400, detail="At least one signer required")

    signers = [
        Signer(email=s.email, name=s.name, role=s.role, routing_order=s.routing_order)
        for s in body.signers
    ]
    envelope = await create_envelope(draft, signers, force=force)
    await _update_envelope(draft.draft_id, str(user.id), envelope.value)
    logger.info(
        "Send requested for draft %s by user %s (force=%s, is_mock=%s)",
        draft.draft_id,
        user.id,
        force,
        envelope.is_mock,
    )
    return SendContractResponse(
        draft_id=draft.draft_id,
        envelope_id=envelope.value,
        is_mock=envelope.is_mock,
        attorney_review_status=draft.attorney_review_status,
        force=force,
    )


@router.get(
    "/contracts/{draft_id}/envelope/{envelope_id}",
    response_model=EnvelopeStatusResponse,
)
async def envelope_status(
    draft_id: str,
    envelope_id: str,
    user: User = Depends(get_current_user),
) -> EnvelopeStatusResponse:
    """Poll DocuSign for envelope status (or mock status).

    Audit fix (security #12 / #20): the ``envelope_id`` in the URL path
    must match the envelope stored on the caller's draft record. A
    mismatch returns 404 so an attacker cannot enumerate envelope IDs
    or poll another account's envelopes through this endpoint.
    """
    record = await _load_draft(draft_id, str(user.id))
    if record.envelope_id is None or record.envelope_id != envelope_id:
        raise HTTPException(
            status_code=404,
            detail="Envelope not associated with this draft",
        )
    status: EnvelopeStatus = await get_envelope_status(envelope_id)
    return EnvelopeStatusResponse(envelope_id=envelope_id, status=status.value)


@router.get("/permits/{jurisdiction}", response_model=PermitChecklist)
def permit_checklist(
    jurisdiction: str,
    pool_length_ft: float = Query(default=30.0, gt=0.0),
    pool_width_ft: float = Query(default=15.0, gt=0.0),
    max_depth_ft: float = Query(default=8.0, gt=0.0),
    has_spa: bool = Query(default=False),
    includes_fence_construction: bool = Query(default=False),
    hoa_applies: bool = Query(default=False),
    user: User = Depends(get_current_user),
) -> PermitChecklist:
    """Return the permit checklist for a jurisdiction.

    Query parameters describe the pool so conditional permits (spa,
    HOA, fence) are filtered appropriately.
    """
    try:
        return generate_permit_checklist(
            jurisdiction=jurisdiction,
            pool_specs=PoolSpecs(
                pool_length_ft=pool_length_ft,
                pool_width_ft=pool_width_ft,
                max_depth_ft=max_depth_ft,
                has_spa=has_spa,
                includes_fence_construction=includes_fence_construction,
                hoa_applies=hoa_applies,
            ),
        )
    except FileNotFoundError:
        supported = list_supported_jurisdictions()
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Jurisdiction '{jurisdiction}' not supported",
                "supported": list(supported),
            },
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
