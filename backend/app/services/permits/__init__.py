"""Permit checklist generation for the Pool Concierge vertical.

Jurisdictions are represented as static YAML data files under
``data/``. Each file is a hand-curated snapshot with a
``last_verified_date`` — callers must surface this to end users so
stale data is not treated as authoritative.
"""
from .checklist import (
    PermitChecklist,
    PermitItem,
    PoolSpecs,
    generate_permit_checklist,
    list_supported_jurisdictions,
)

__all__ = [
    "PermitChecklist",
    "PermitItem",
    "PoolSpecs",
    "generate_permit_checklist",
    "list_supported_jurisdictions",
]
