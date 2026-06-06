"""Provider adapters — one place per external service.

Before this layer existed, Exa was wrapped in three independent modules
(``services/crews/tools/exa_search.py``, ``services/data_sources/connectors/exa.py``,
``services/research/exa_search.py``) and Gemini in two. Each had its own
retry policy, error handling, and missing-key behaviour — so a provider
change was a multi-place edit.

Now each provider has exactly one adapter module here. Domain code
imports from this layer; SDK access lives nowhere else.

Public re-exports below; explicit so editors can jump to symbol.
"""
from .exa import ExaProvider, exa_provider
from .gemini import GeminiProvider, gemini_provider

__all__ = ["ExaProvider", "exa_provider", "GeminiProvider", "gemini_provider"]
