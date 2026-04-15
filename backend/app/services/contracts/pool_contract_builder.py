"""Render pool installation contracts from Jinja2 templates to PDF.

Pipeline
--------
1. Load the Jinja2 markdown template + its YAML metadata sidecar.
2. Render the markdown with the provided buyer / contractor / quote DTOs.
3. Convert markdown -> HTML via ``markdown2``.
4. Convert HTML -> PDF via WeasyPrint when available; otherwise fall back
   to a plain-text reportlab PDF and surface the limitation in metadata.
5. Hash the PDF (SHA-256) and return everything wrapped in a
   :class:`ContractDraft`.

The ``attorney_review_status`` on every returned draft is whatever the
template metadata says. In practice every template in the repo starts at
``PENDING-LEGAL`` and the API layer refuses to send until counsel flips
the metadata. The builder never mutates ``last_reviewed_date``.
"""
from __future__ import annotations

import hashlib
import html
import io
import logging
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

import markdown2
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .dto import (
    AttorneyReviewStatus,
    BuyerInfo,
    ContractDraft,
    ContractorInfo,
    Quote,
)

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_DEFAULT_TEMPLATE_KEY = "tx_pool_installation_v1"

# Security audit #1 / code-review #12: template_key is user-supplied and
# was concatenated directly into a filesystem path. An attacker could
# pass ``../../etc/passwd`` or similar to read arbitrary YAML/template
# files on disk. The allowlist is the authoritative gate; the slug
# validation in ``_load_metadata`` is a second layer of defence mirrored
# from ``permits/checklist.py:70``.
_ALLOWED_TEMPLATES: frozenset[str] = frozenset({"tx_pool_installation_v1"})


class ListingView(Protocol):
    """Structural view of a PoolListing sufficient for contract rendering.

    Adapters can pass an ORM ``PoolListing`` or a plain object with these
    attributes — we never import the ORM model here so this module stays
    usable in unit tests without a database.
    """

    address: str


# ---------------------------------------------------------------------------
# Jinja environment
# ---------------------------------------------------------------------------
def _build_env() -> Environment:
    """Construct a strict Jinja2 environment for contract rendering.

    Audit fix (security #8): previous code only enabled autoescape for
    ``.html`` extensions, leaving the ``.md.j2`` contract template
    unescaped. Because the rendered markdown is later served back in an
    API response and converted to HTML for preview, any unescaped user
    input (buyer name, address, contractor name, etc.) could surface as
    stored XSS. We now enable autoescape by default for every template;
    the markdown template uses plain ``{{ var }}`` substitution which is
    preserved as readable text once Jinja escapes the HTML-sensitive
    characters.

    ``StrictUndefined`` makes missing variables raise instead of silently
    rendering to an empty string — critical for legal documents.
    """
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(default=True),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


# ---------------------------------------------------------------------------
# Metadata loader
# ---------------------------------------------------------------------------
def _load_metadata(template_key: str) -> dict[str, Any]:
    """Read the YAML sidecar for ``<template_key>.metadata.yaml``.

    Audit fix (security #1, code-review #12): mirror the
    ``isalnum()+underscore`` guard from ``permits/checklist.py:70`` as a
    second layer of defence against path traversal. The top-level
    allowlist in :func:`build_pool_contract` is the authoritative gate;
    this check ensures any code path that reaches metadata loading is
    still safe even if the allowlist is bypassed in future callers.
    """
    if not template_key or not template_key.replace("_", "").isalnum():
        raise ValueError(f"Invalid template_key slug: {template_key!r}")
    meta_path = _TEMPLATES_DIR / f"{template_key}.metadata.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing metadata for template: {template_key}")
    with meta_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Metadata for {template_key} is not a mapping")
    return data


# ---------------------------------------------------------------------------
# PDF conversion
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _PdfResult:
    pdf_bytes: bytes
    renderer: str


def _html_to_pdf(html: str) -> _PdfResult:
    """Convert HTML to PDF, preferring WeasyPrint.

    Falls back to a plain-text reportlab PDF if WeasyPrint cannot be
    imported or fails at runtime (WeasyPrint requires GTK/Pango which
    is not always present on Windows).
    """
    try:
        from weasyprint import HTML  # type: ignore[import-not-found]

        pdf_bytes = HTML(string=html).write_pdf()
        if pdf_bytes:
            return _PdfResult(pdf_bytes=pdf_bytes, renderer="weasyprint")
    except Exception as exc:  # noqa: BLE001 — intentional broad fallback
        logger.warning("WeasyPrint unavailable (%s); using reportlab fallback", exc)

    return _PdfResult(pdf_bytes=_reportlab_fallback(html), renderer="reportlab-plain")


def _reportlab_fallback(html: str) -> bytes:
    """Render an HTML blob as a minimal, plain-text PDF.

    This is intentionally bare-bones: the output is not laid out like the
    Markdown source, but the full text content survives so counsel can
    still review the artifact. Callers should prefer WeasyPrint.
    """
    from reportlab.lib.pagesizes import LETTER
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    margin = 54.0
    line_height = 12.0
    y = height - margin

    # Strip tags crudely. The source is trusted template output, so we
    # are not defending against malicious HTML — only flattening for a
    # readable plain-text PDF.
    import re

    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    pdf.setFont("Helvetica", 9)
    for raw_line in text.splitlines():
        # Simple word-wrap at ~95 chars
        line = raw_line.rstrip()
        while len(line) > 95:
            cut = line.rfind(" ", 0, 95)
            if cut <= 0:
                cut = 95
            pdf.drawString(margin, y, line[:cut])
            line = line[cut:].lstrip()
            y -= line_height
            if y < margin:
                pdf.showPage()
                pdf.setFont("Helvetica", 9)
                y = height - margin
        pdf.drawString(margin, y, line)
        y -= line_height
        if y < margin:
            pdf.showPage()
            pdf.setFont("Helvetica", 9)
            y = height - margin

    pdf.showPage()
    pdf.save()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Markdown rendering helpers
# ---------------------------------------------------------------------------
def _markdown_to_html(markdown_body: str, title: str) -> str:
    """Wrap rendered markdown in a minimal HTML document.

    Audit fix (security #9): the ``title`` value originates in the
    template metadata YAML but nothing prevents a future template author
    (or a future loader bug) from inserting HTML-sensitive characters.
    Escape it before splicing into the ``<title>`` element.
    """
    body_html = markdown2.markdown(
        markdown_body,
        extras=["tables", "fenced-code-blocks", "break-on-newline"],
    )
    return (
        "<!doctype html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='utf-8'/>\n"
        f"<title>{html.escape(title)}</title>\n"
        "<style>\n"
        "body { font-family: Georgia, 'Times New Roman', serif; "
        "max-width: 720px; margin: 40px auto; color: #111; line-height: 1.5; }\n"
        "h1, h2, h3 { font-family: 'Helvetica', Arial, sans-serif; }\n"
        "table { border-collapse: collapse; width: 100%; margin: 1em 0; }\n"
        "th, td { border: 1px solid #999; padding: 6px 10px; text-align: left; }\n"
        "th { background: #eee; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f"{body_html}\n"
        "</body>\n"
        "</html>\n"
    )


def _coerce_review_status(raw: object) -> AttorneyReviewStatus:
    """Coerce a metadata value into the canonical review status literal."""
    normalized = str(raw or "PENDING-LEGAL").strip().upper()
    if normalized in {"APPROVED", "BLOCKED"}:
        return normalized  # type: ignore[return-value]
    return "PENDING-LEGAL"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_pool_contract(
    buyer: BuyerInfo,
    contractor: ContractorInfo,
    listing: ListingView,
    quote: Quote,
    template_key: str = _DEFAULT_TEMPLATE_KEY,
    effective_date: date | None = None,
) -> ContractDraft:
    """Render a pool installation contract to PDF.

    Parameters
    ----------
    buyer, contractor, listing, quote
        Plain-data DTOs describing the deal.
    template_key
        Key into the Jinja template library; defaults to Texas v1.
    effective_date
        Optional override; defaults to today.

    Returns
    -------
    :class:`ContractDraft`
        The rendered artifact. ``attorney_review_status`` is carried
        through from the template metadata — callers must check it
        before sending anything to DocuSign.

    Raises
    ------
    ValueError
        If ``template_key`` is not on the :data:`_ALLOWED_TEMPLATES`
        allowlist (security audit #1 — blocks path traversal).
    """
    # Security audit #1: authoritative allowlist gate. Keep this here
    # even though ``_load_metadata`` also validates the slug, so callers
    # that bypass the metadata load still can't smuggle arbitrary keys
    # into the Jinja ``get_template`` call below.
    if template_key not in _ALLOWED_TEMPLATES:
        raise ValueError(f"unknown template_key: {template_key!r}")
    metadata = _load_metadata(template_key)
    env = _build_env()
    template = env.get_template(f"{template_key}.md.j2")

    jurisdiction_city = str(metadata.get("default_city", "Plano"))
    jurisdiction_county = str(metadata.get("jurisdiction", "Collin County, Texas"))

    markdown_body = template.render(
        buyer=buyer.model_dump(),
        contractor=contractor.model_dump(),
        listing={"address": getattr(listing, "address", "")},
        quote=quote.model_dump(mode="json"),
        effective_date=(effective_date or date.today()).isoformat(),
        jurisdiction_city=jurisdiction_city,
        jurisdiction_county=jurisdiction_county,
    )

    title = str(metadata.get("document_title", "Pool Installation Agreement"))
    html = _markdown_to_html(markdown_body, title=title)
    pdf_result = _html_to_pdf(html)

    enriched_metadata: dict[str, object] = {
        **metadata,
        "renderer": pdf_result.renderer,
        "effective_date": (effective_date or date.today()).isoformat(),
    }

    return ContractDraft(
        draft_id=str(uuid.uuid4()),
        template_key=template_key,
        pdf_bytes=pdf_result.pdf_bytes,
        html=html,
        markdown=markdown_body,
        metadata=enriched_metadata,
        attorney_review_status=_coerce_review_status(
            metadata.get("attorney_review_status")
        ),
        sha256=hashlib.sha256(pdf_result.pdf_bytes).hexdigest(),
    )
