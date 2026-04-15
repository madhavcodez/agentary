"""Immutable DTOs for the pool contract subsystem.

All data classes are ``frozen`` Pydantic models so they can be used
safely across async boundaries, serialised, and hashed for caching.

These DTOs are intentionally self-contained: the contract builder only
needs a small view of the ``PoolListing`` record (address + specs), and
callers are expected to adapt richer ORM objects into these plain-data
shapes at the edge.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    """Base class for immutable Pydantic DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class BuyerInfo(_Frozen):
    """The buyer / homeowner side of the contract."""

    full_name: str
    email: str
    phone: str
    billing_address: str
    installation_address: str


class ContractorInfo(_Frozen):
    """The installing contractor."""

    company_name: str
    license_number: str
    contact_name: str
    email: str
    phone: str
    business_address: str


class PaymentMilestone(_Frozen):
    """One line item in the payment schedule.

    ``percent`` is expressed as a float between 0 and 100 and is what
    gets rendered in the contract body; ``amount_usd`` is the absolute
    value for convenience and is recomputed by the builder when a Quote
    total is available.
    """

    name: str
    description: str
    percent: float = Field(ge=0.0, le=100.0)
    amount_usd: float = Field(ge=0.0)


class Quote(_Frozen):
    """The priced pool specification this contract locks in."""

    quote_id: str
    pool_length_ft: float = Field(gt=0.0)
    pool_width_ft: float = Field(gt=0.0)
    shallow_end_depth_ft: float = Field(gt=0.0)
    deep_end_depth_ft: float = Field(gt=0.0)
    pool_shape: str
    included_equipment: tuple[str, ...]
    total_price_usd: float = Field(ge=0.0)
    start_date: date
    substantial_completion_date: date
    warranty_years: int = Field(ge=0)
    payment_schedule: tuple[PaymentMilestone, ...]


AttorneyReviewStatus = Literal["PENDING-LEGAL", "APPROVED", "BLOCKED"]


class ContractDraft(_Frozen):
    """The rendered contract artifact returned to callers.

    ``pdf_bytes`` is always populated; ``html`` holds the rendered HTML
    for preview; ``metadata`` is a shallow dict copy of the template
    metadata YAML; ``attorney_review_status`` is the canonical gating
    flag — the API refuses to send anything that is not ``APPROVED``.
    """

    draft_id: str
    template_key: str
    pdf_bytes: bytes
    html: str
    markdown: str
    metadata: dict[str, object]
    attorney_review_status: AttorneyReviewStatus
    sha256: str
