"""AI-driven KPI resolver for PPTX decks (RR-1 Phase B).

Given the text elements ingested from a PowerPoint deck and a target reporting
period, produce a list of proposals describing which strings should be
replaced and with what new value.

Each proposal is one of:

* ``mapping`` - resolved to a single supported KPI at portfolio scope; the
  patcher can apply it directly once the user confirms.
* ``ambiguous_scope`` - the value could plausibly belong to multiple scopes
  (e.g. portfolio vs a specific fund) and the AI could not disambiguate from
  surrounding context.  Per design decision DD-2 we never silently fall back
  to portfolio.
* ``unsupported_kpi`` - the value clearly represents a KPI but it is outside
  the v1 catalog (e.g. fund-level rent, NOI).
* ``skipped`` - the value is not a KPI, or is a comparison value we cannot
  refresh (e.g. \"FY24 vs FY25\").

The Anthropic client is injectable so tests can run without network access.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.api.analytics import _csv_kpis, _snapshot_kpis
from app.config import settings
from app.core.kpi_catalog import KPI_CATALOG, format_value, get_kpi
from app.models.database import ReportingPeriod
from app.parsers.pptx_ingestor import TextAddress, TextElement

# ── Candidate extraction ──────────────────────────────────────────────

DIGIT_RE = re.compile(r"\d")
# Tokens that suggest the run carries a KPI value rather than free prose.
UNIT_RE = re.compile(
    r"(M\s*€|Mio\.?|Mrd\.?|k\s*€|€|EUR|m²|sqm|qm|%|Jahre|years?|pcs|Stk\.?)",
    re.IGNORECASE,
)
# A loose date matcher; ``07.05.2025`` or ``2025-05-07`` should not count as a KPI value.
DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\b20\d{2}\b")
# A KPI value looks like a number with an optional unit prefix and/or suffix,
# e.g. ``12,5 M€`` / ``EUR 12,500,000`` / ``€ 12,5 M`` / ``1.500 m²`` /
# ``8 %`` / ``120``.  Anything that interleaves letters with the leading
# number (``Q2 overview``) is treated as prose, not a value.
_UNIT_AFFIX = (
    r"(?:M\s*€|Mio\.?|Mrd\.?|k\s*€|€|EUR|USD|GBP|CHF|"
    r"m²|sqm|qm|%|Jahre|years?|pcs|Stk\.?)"
)
_MULTIPLIER_SUFFIX = r"(?:\s*(?:M|Mio\.?|Mrd\.?|k))?"
NUMERIC_VALUE_RE = re.compile(
    r"^\s*"
    rf"(?:{_UNIT_AFFIX}\s*)?"
    r"-?\d[\d.,'\s]*"
    rf"{_MULTIPLIER_SUFFIX}"
    rf"\s*(?:{_UNIT_AFFIX})?"
    r"\s*$",
    re.IGNORECASE,
)


@dataclass
class Candidate:
    idx: int
    address: TextAddress
    original_value: str
    slide_idx: int
    slide_title: str
    label_context: str
    neighborhood: str


def _looks_like_kpi(text: str) -> bool:
    if not DIGIT_RE.search(text):
        return False
    stripped = text.strip()
    if not stripped:
        return False
    if DATE_RE.fullmatch(stripped):
        return False
    return bool(NUMERIC_VALUE_RE.match(stripped))


def _slide_title(elements: list[TextElement], slide_idx: int) -> str:
    """First non-empty text frame run on the slide.

    Slide titles are typically the first textbox added; this is a heuristic
    but works for the decks we have seen so far.
    """
    for element in elements:
        if element.address.slide_idx != slide_idx:
            continue
        if element.address.kind != "text_frame":
            continue
        text = element.text.strip()
        if text and not _looks_like_kpi(text):
            return text[:120]
    return ""


def _label_for(elements: list[TextElement], target: TextElement) -> str:
    """Concatenate the non-numeric text that precedes the target on the same slide.

    Slides typically place the value in its own textbox / table cell with the
    descriptive label in a sibling shape.  We walk all elements in reading
    order on the same slide and stop at the target, keeping every prose run
    seen so far.  Used as the label hint passed to the AI.
    """
    addr = target.address
    same_slide = [e for e in elements if e.address.slide_idx == addr.slide_idx]
    parts: list[str] = []
    for element in same_slide:
        if element is target:
            break
        text = element.text.strip()
        if not text or _looks_like_kpi(text):
            continue
        parts.append(text)
    return " ".join(parts)[-200:]


def _neighborhood(elements: list[TextElement], target: TextElement) -> str:
    """Free-form context: every non-numeric run on the same slide."""
    addr = target.address
    same_slide = [e for e in elements if e.address.slide_idx == addr.slide_idx]
    parts: list[str] = []
    for element in same_slide:
        if element is target:
            continue
        text = element.text.strip()
        if not text or _looks_like_kpi(text):
            continue
        parts.append(text)
    snippet = " | ".join(parts)
    return snippet[:400]


def collect_candidates(elements: list[TextElement]) -> list[Candidate]:
    candidates: list[Candidate] = []
    title_cache: dict[int, str] = {}
    for element in elements:
        if not _looks_like_kpi(element.text):
            continue
        slide_idx = element.address.slide_idx
        if slide_idx not in title_cache:
            title_cache[slide_idx] = _slide_title(elements, slide_idx)
        candidates.append(
            Candidate(
                idx=len(candidates),
                address=element.address,
                original_value=element.text,
                slide_idx=slide_idx,
                slide_title=title_cache[slide_idx],
                label_context=_label_for(elements, element),
                neighborhood=_neighborhood(elements, element),
            )
        )
    return candidates


# ── LLM interaction ───────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You map slide text in a real-estate PowerPoint deck to KPIs from a fixed catalog.

You will receive a JSON array of CANDIDATES extracted from one deck.  Each
candidate has:
  - idx (integer)
  - original_value (the literal text run, e.g. "12,5 M€")
  - slide_title (string, may be empty)
  - label_context (the closest preceding label, e.g. "Total rent")
  - neighborhood (other non-numeric text on the same slide)

The catalog will be provided as JSON: id, label, aliases, scope, format hint.
The catalog only contains PORTFOLIO-scope KPIs in v1.  If a candidate clearly
belongs to a single fund or property (e.g. "GLIF rent") return
`unsupported_kpi`.  If the scope is ambiguous (e.g. just "Total rent" with no
fund/portfolio context anywhere on the slide) return `ambiguous_scope` -
NEVER silently default to portfolio.

Respond with a single JSON object ONLY, no prose, matching this shape:

{
  "decisions": [
    {
      "idx": 0,
      "decision": "mapping" | "ambiguous_scope" | "unsupported_kpi" | "skipped",
      "kpi_id": "<catalog id, when decision = mapping>",
      "confidence": 0.0..1.0,
      "reasoning": "<short, English>",
      "label_observed": "<for unsupported_kpi: the label you saw>"
    }
  ]
}

Rules:
- Output JSON only, no markdown fences, no commentary.
- Skip candidates that are page numbers, dates, headcounts that have no
  catalog match, or comparison values you cannot refresh.
- Return a decision for every candidate idx, in order.
"""


def _format_catalog(available_kpis: Iterable[str]) -> str:
    items = []
    for kpi_id in available_kpis:
        spec = KPI_CATALOG[kpi_id]
        items.append(
            {
                "id": spec.kpi_id,
                "label": spec.label,
                "aliases": spec.aliases,
                "scope": spec.scope,
                "format_hint": spec.format_hint,
            }
        )
    return json.dumps(items, ensure_ascii=False)


def _candidates_payload(candidates: list[Candidate]) -> str:
    items = [
        {
            "idx": c.idx,
            "original_value": c.original_value,
            "slide_title": c.slide_title,
            "label_context": c.label_context,
            "neighborhood": c.neighborhood,
        }
        for c in candidates
    ]
    return json.dumps(items, ensure_ascii=False)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # Drop opening fence and optional language tag.
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


def _parse_decisions(raw_text: str) -> list[dict[str, Any]]:
    cleaned = _strip_code_fences(raw_text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response was not valid JSON: {exc}; raw={raw_text[:300]}")
    if not isinstance(parsed, dict):
        raise ValueError("AI response was not a JSON object")
    decisions = parsed.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("AI response missing `decisions` array")
    return decisions


def _get_default_client():
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env"
        )
    import anthropic

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _ask_claude(
    candidates: list[Candidate],
    available_kpis: list[str],
    client: Any,
    model: str = "claude-sonnet-4-6",
) -> list[dict[str, Any]]:
    user_payload = json.dumps(
        {
            "catalog": json.loads(_format_catalog(available_kpis)),
            "candidates": json.loads(_candidates_payload(candidates)),
        },
        ensure_ascii=False,
    )
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_payload}],
    )
    text_parts: list[str] = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(getattr(block, "text", ""))
    raw = "\n".join(text_parts).strip()
    if not raw:
        raise ValueError("AI response contained no text")
    return _parse_decisions(raw)


# ── Proposal building ─────────────────────────────────────────────────

ProposalKind = str  # "mapping" | "ambiguous_scope" | "unsupported_kpi" | "skipped"


def _kpi_values_for_period(db: Session, period: ReportingPeriod) -> dict[str, Any]:
    return {**_csv_kpis(db, period), **_snapshot_kpis(db, period)}


def _available_kpi_ids(values: dict[str, Any]) -> list[str]:
    return [kpi_id for kpi_id in KPI_CATALOG if values.get(kpi_id) is not None]


def _address_dict(address: TextAddress) -> dict[str, Any]:
    return {
        "slide_idx": address.slide_idx,
        "shape_id": address.shape_id,
        "kind": address.kind,
        "row": address.row,
        "col": address.col,
        "paragraph_idx": address.paragraph_idx,
        "run_idx": address.run_idx,
    }


def _make_proposal(
    candidate: Candidate,
    decision: dict[str, Any],
    values: dict[str, Any],
) -> dict[str, Any]:
    kind = decision.get("decision")
    base = {
        "idx": candidate.idx,
        "address": _address_dict(candidate.address),
        "slide_idx": candidate.slide_idx,
        "slide_title": candidate.slide_title,
        "label_context": candidate.label_context,
        "original_value": candidate.original_value,
        "kind": kind,
        "confidence": decision.get("confidence"),
        "reasoning": decision.get("reasoning"),
    }

    if kind == "mapping":
        kpi_id = decision.get("kpi_id")
        spec = get_kpi(kpi_id) if isinstance(kpi_id, str) else None
        raw_value = values.get(kpi_id) if spec else None
        if not spec or raw_value is None:
            base["kind"] = "unsupported_kpi"
            base["label_observed"] = decision.get("label_observed") or candidate.label_context
            base["reasoning"] = (
                base.get("reasoning") or ""
            ) + " | Catalog/value lookup failed."
            return base
        base["kpi_id"] = kpi_id
        base["scope"] = spec.scope
        base["new_value"] = format_value(raw_value, spec.format_hint)
        return base

    if kind == "ambiguous_scope":
        base["candidate_kpi_id"] = decision.get("kpi_id")
        return base

    if kind == "unsupported_kpi":
        base["label_observed"] = decision.get("label_observed") or candidate.label_context
        return base

    # Default to skipped if the AI returned anything else.
    base["kind"] = "skipped"
    return base


def _summarise(proposals: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "candidates_total": len(proposals),
        "mappings": 0,
        "ambiguous": 0,
        "unsupported": 0,
        "skipped": 0,
    }
    for proposal in proposals:
        kind = proposal.get("kind")
        if kind == "mapping":
            summary["mappings"] += 1
        elif kind == "ambiguous_scope":
            summary["ambiguous"] += 1
        elif kind == "unsupported_kpi":
            summary["unsupported"] += 1
        else:
            summary["skipped"] += 1
    return summary


def resolve_with_ai(
    db: Session,
    elements: list[TextElement],
    period_id: int,
    client: Any | None = None,
    model: str = "claude-sonnet-4-6",
) -> dict[str, Any]:
    """Run the full AI mapping pass for a deck against a period.

    Returns a dict suitable for storing in ``PptxRefreshJob.proposals_json``.
    Raises if the period does not exist or the AI response cannot be parsed.
    """
    period = db.get(ReportingPeriod, period_id)
    if not period:
        raise ValueError(f"Period {period_id} not found")

    values = _kpi_values_for_period(db, period)
    available = _available_kpi_ids(values)
    candidates = collect_candidates(elements)

    if not candidates:
        return {
            "mode": "ai",
            "period_id": period_id,
            "period_status": period.status,
            "available_kpis": available,
            "proposals": [],
            "summary": _summarise([]),
        }

    if not available:
        proposals = [
            _make_proposal(
                candidate,
                {
                    "decision": "unsupported_kpi",
                    "label_observed": candidate.label_context,
                    "reasoning": "No KPI values available for the selected period.",
                },
                values,
            )
            for candidate in candidates
        ]
        return {
            "mode": "ai",
            "period_id": period_id,
            "period_status": period.status,
            "available_kpis": available,
            "proposals": proposals,
            "summary": _summarise(proposals),
        }

    if client is None:
        client = _get_default_client()

    decisions = _ask_claude(candidates, available, client, model=model)
    by_idx = {decision.get("idx"): decision for decision in decisions if isinstance(decision, dict)}

    proposals: list[dict[str, Any]] = []
    for candidate in candidates:
        decision = by_idx.get(candidate.idx)
        if decision is None:
            decision = {
                "decision": "skipped",
                "reasoning": "AI returned no decision for this candidate.",
            }
        proposals.append(_make_proposal(candidate, decision, values))

    return {
        "mode": "ai",
        "period_id": period_id,
        "period_status": period.status,
        "available_kpis": available,
        "proposals": proposals,
        "summary": _summarise(proposals),
    }
