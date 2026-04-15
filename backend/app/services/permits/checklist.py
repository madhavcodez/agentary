"""Generate a jurisdiction-specific permit checklist for pool installs.

Data lives in ``data/<jurisdiction>.yaml``. Each YAML document must
include a ``last_verified_date`` in ISO format so callers can render a
staleness banner — Agentary never treats a permit checklist as
authoritative without showing when it was last verified.

The functions here are pure (no I/O besides reading bundled YAML, no
network calls). They are trivially mockable in tests.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

_DATA_DIR = Path(__file__).parent / "data"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PoolSpecs(_Frozen):
    """Minimal spec surface used to conditionally include permits."""

    pool_length_ft: float = Field(gt=0.0)
    pool_width_ft: float = Field(gt=0.0)
    max_depth_ft: float = Field(gt=0.0)
    has_spa: bool = False
    includes_fence_construction: bool = False
    hoa_applies: bool = False


PullerType = Literal["contractor_typically_pulls", "homeowner_pulls"]


class PermitItem(_Frozen):
    """One permit or authorisation line item."""

    id: str
    name: str
    issuing_office: str
    est_cost_usd: float = Field(ge=0.0)
    est_processing_days: int = Field(ge=0)
    application_url: str
    prefilled_form_url: str | None = None
    required_attachments: tuple[str, ...] = ()
    statutory_basis: str | None = None
    puller: PullerType
    notes: str | None = None


class PermitChecklist(_Frozen):
    """Rendered checklist returned to callers."""

    jurisdiction: str
    jurisdiction_name: str
    state: str
    last_verified_date: str
    items: tuple[PermitItem, ...]
    statutory_notes: tuple[str, ...] = ()


def _load_jurisdiction(jurisdiction: str) -> dict:
    """Load and validate the YAML file for a jurisdiction slug."""
    # Guard against path traversal: slug must be a simple identifier.
    if not jurisdiction or not jurisdiction.replace("_", "").isalnum():
        raise ValueError(f"Invalid jurisdiction slug: {jurisdiction!r}")
    path = _DATA_DIR / f"{jurisdiction}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No permit data bundled for jurisdiction: {jurisdiction}"
        )
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Permit data for {jurisdiction} is not a mapping")
    return data


def list_supported_jurisdictions() -> tuple[str, ...]:
    """Return the slugs of every bundled jurisdiction YAML."""
    if not _DATA_DIR.exists():
        return ()
    return tuple(sorted(p.stem for p in _DATA_DIR.glob("*.yaml")))


def _item_applies(raw: dict, pool_specs: PoolSpecs) -> bool:
    """Apply simple conditional rules declared in YAML."""
    only_if = raw.get("only_if")
    if only_if is None:
        return True
    if only_if == "has_spa":
        return pool_specs.has_spa
    if only_if == "includes_fence_construction":
        return pool_specs.includes_fence_construction
    if only_if == "hoa_applies":
        return pool_specs.hoa_applies
    # Unknown conditional — default to including so reviewers see it.
    return True


def _build_item(raw: dict) -> PermitItem:
    return PermitItem(
        id=str(raw["id"]),
        name=str(raw["name"]),
        issuing_office=str(raw["issuing_office"]),
        est_cost_usd=float(raw.get("est_cost_usd", 0.0)),
        est_processing_days=int(raw.get("est_processing_days", 0)),
        application_url=str(raw.get("application_url", "")),
        prefilled_form_url=(
            str(raw["prefilled_form_url"]) if raw.get("prefilled_form_url") else None
        ),
        required_attachments=tuple(str(a) for a in raw.get("required_attachments", ())),
        statutory_basis=(
            str(raw["statutory_basis"]) if raw.get("statutory_basis") else None
        ),
        puller=_coerce_puller(raw.get("puller", "contractor_typically_pulls")),
        notes=str(raw["notes"]) if raw.get("notes") else None,
    )


def _coerce_puller(raw: object) -> PullerType:
    value = str(raw or "").strip()
    if value == "homeowner_pulls":
        return "homeowner_pulls"
    return "contractor_typically_pulls"


def generate_permit_checklist(
    jurisdiction: str = "plano_tx",
    pool_specs: PoolSpecs | None = None,
) -> PermitChecklist:
    """Produce the permit checklist for a jurisdiction and pool.

    Parameters
    ----------
    jurisdiction
        Slug under ``data/``. Defaults to ``plano_tx``.
    pool_specs
        Optional; when supplied, permits tagged with ``only_if`` are
        filtered against these specs. When omitted, every permit is
        returned so reviewers can see the full list.
    """
    data = _load_jurisdiction(jurisdiction)
    specs = pool_specs or PoolSpecs(
        pool_length_ft=30.0,
        pool_width_ft=15.0,
        max_depth_ft=8.0,
        has_spa=False,
        includes_fence_construction=False,
        hoa_applies=False,
    )

    raw_items = data.get("permits", []) or []
    items = tuple(
        _build_item(raw) for raw in raw_items if _item_applies(raw, specs)
    )

    return PermitChecklist(
        jurisdiction=jurisdiction,
        jurisdiction_name=str(data.get("jurisdiction_name", jurisdiction)),
        state=str(data.get("state", "")),
        last_verified_date=str(data.get("last_verified_date", "")),
        items=items,
        statutory_notes=tuple(str(n) for n in data.get("statutory_notes", ())),
    )
