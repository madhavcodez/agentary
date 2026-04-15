"""Contractor discovery, license verification, and quote orchestration.

Stream C of the Pool Concierge vertical. Given a scored
:class:`app.models.pool_listing.PoolListing`, this package:

1. Discovers in-ground pool contractors near the listing's ZIP via Yelp
   and Google Places (``discovery``).
2. Verifies each contractor against public licensing data — currently TX
   TDLR (``license_verifier``).
3. Places outbound voice calls (TCPA-compliant disclosure first) through
   the existing Pipecat + Twilio + Gemini Live pipeline to request a
   rough ballpark quote (``quote_caller``).
4. Ranks the returned quotes by price, ETA, and rating
   (``quote_ranker``).

Higher-level orchestration lives in
``app.verticals.pool_concierge.contractor_pipeline``.
"""
from .discovery import ContractorCandidate, discover_pool_contractors
from .license_verifier import LicenseStatus, verify_license, verify_tx_license
from .quote_caller import (
    PoolSpecs,
    QuoteResult,
    build_disclosure_preamble,
    request_quote_via_voice,
)
from .quote_ranker import RankedQuote, rank_quotes

__all__ = [
    "ContractorCandidate",
    "discover_pool_contractors",
    "LicenseStatus",
    "verify_license",
    "verify_tx_license",
    "PoolSpecs",
    "QuoteResult",
    "build_disclosure_preamble",
    "request_quote_via_voice",
    "RankedQuote",
    "rank_quotes",
]
