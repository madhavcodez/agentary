"""Pool installation contract drafting services.

Stream D of the Pool Concierge vertical. This package generates
Texas (Plano-specific) pool installation contracts as PDFs and, when
DocuSign credentials are configured, can create signable envelopes.

Important safety properties
---------------------------
* Every template is marked ``ATTORNEY REVIEW REQUIRED`` and the metadata
  ``last_reviewed_date`` is ``PENDING-LEGAL`` until counsel signs off.
* The DocuSign client falls back to mock envelope IDs when credentials
  are missing. No envelope is ever created against the live DocuSign API
  without an explicit ``force=True`` request AND configured credentials.
"""

from .dto import (
    BuyerInfo,
    ContractDraft,
    ContractorInfo,
    PaymentMilestone,
    Quote,
)
from .pool_contract_builder import build_pool_contract

__all__ = [
    "BuyerInfo",
    "ContractDraft",
    "ContractorInfo",
    "PaymentMilestone",
    "Quote",
    "build_pool_contract",
]
