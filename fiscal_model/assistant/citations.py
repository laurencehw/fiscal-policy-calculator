"""
Citation post-processing.

The model is instructed to emit ``[^N]`` footnote markers attached to every
substantive claim, then a ``## Sources`` section listing each as
``[^N]: <author> (<year>), "<title>", <URL>``. This module:

1. Extracts the ``[^N]`` markers and the Sources section from the answer.
2. Cross-references each marker against the tool-call provenance trail
   collected by :class:`AssistantTools`.
3. Strips unsupported markers and replaces them with a clearly-marked
   ``[citation needed]`` placeholder.

The goal is not to second-guess the model's writing, but to make it
structurally hard to ship an unsupported numerical claim.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

_CITATION_MARKER_RE = re.compile(r"\[\^(\d+)\]")
_SOURCES_HEADING_RE = re.compile(
    r"(?m)^\s*##+\s*Sources\s*$|^\s*\*\*Sources\*\*\s*$"
)
_SOURCE_ENTRY_RE = re.compile(r"(?m)^\s*\[\^(\d+)\]:\s*(.*)$")
_URL_RE = re.compile(r"https?://[^\s)\]}>\"']+")


def _domain(url: str) -> str:
    """Normalized registrable-ish domain for loose matching (drops ``www.``)."""
    netloc = urlparse(url.strip()).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def _parse_sources(sources: str | None) -> dict[int, str]:
    """Map each ``[^N]: ...`` Sources line to its raw text."""
    if not sources:
        return {}
    return {int(n): body.strip() for n, body in _SOURCE_ENTRY_RE.findall(sources)}


def _grounded_domains(
    provenance: list[dict[str, Any]],
    web_search_citations: list[str] | None,
) -> set[str]:
    """Domains the model was actually given this turn (the grounded set)."""
    domains: set[str] = set()
    for p in provenance:
        for url in p.get("urls") or []:
            domains.add(_domain(url))
        # ``fetch_url`` carries its URL in the call args, not the result body.
        if p.get("tool") == "fetch_url":
            url = (p.get("args") or {}).get("url")
            if url:
                domains.add(_domain(url))
    for url in web_search_citations or []:
        domains.add(_domain(url))
    domains.discard("")
    return domains


def extract_citation_markers(text: str) -> list[int]:
    """Return all distinct ``N`` values found in inline ``[^N]`` markers."""
    return sorted({int(m) for m in _CITATION_MARKER_RE.findall(text)})


def split_body_and_sources(text: str) -> tuple[str, str | None]:
    """Split the answer into prose-body and the ``## Sources`` block, if any."""
    match = _SOURCES_HEADING_RE.search(text)
    if not match:
        return text, None
    body = text[: match.start()].rstrip()
    sources = text[match.end():].strip()
    return body, sources


def annotate_unsupported(
    text: str,
    provenance: list[dict[str, Any]],
    web_search_citations: list[str] | None = None,
) -> tuple[str, list[int]]:
    """Replace unsupported markers with a ``[citation needed]`` tag.

    Each ``[^N]`` is checked individually against what the model was actually
    given this turn:

    * If the Sources section maps ``N`` to an **external URL**, the marker is
      kept only when that URL's domain is in the grounded set (a ``fetch_url``
      target, a ``web_search`` citation, or a ``url``/``source_url`` surfaced
      by ``search_knowledge``/``query_fred``). A URL the model never received
      is treated as fabricated and stripped — even when other tools ran.
    * If the Sources entry carries **no URL** (an app-internal claim — scoring
      engine, baseline, validation scorecard), the marker is kept when at
      least one internal tool ran this turn, since those have no URL to match.
    * Markers with no Sources entry at all are kept only when an internal tool
      ran (preserves terse internal-only answers); otherwise stripped.

    Returns ``(annotated_text, stripped_markers)``.
    """
    markers = extract_citation_markers(text)
    if not markers:
        return text, []

    has_internal_tool = any(
        p.get("tool")
        in {
            "get_app_scoring_context",
            "get_cbo_baseline",
            "get_validation_scorecard",
            "list_presets",
            "get_preset",
            "score_hypothetical_policy",
            "search_knowledge",
            "query_fred",
        }
        for p in provenance
    )

    _, sources = split_body_and_sources(text)
    sources_map = _parse_sources(sources)
    grounded = _grounded_domains(provenance, web_search_citations)

    def _marker_supported(n: int) -> bool:
        entry = sources_map.get(n)
        if entry:
            urls = _URL_RE.findall(entry)
            if urls:
                # Cites an external source: it must be one we actually fetched.
                return any(_domain(u) in grounded for u in urls)
            # Sources entry with no URL → internal/app claim.
            return has_internal_tool
        # No Sources entry for this marker → only trust if an internal tool ran.
        return has_internal_tool

    supported = {n for n in markers if _marker_supported(n)}
    if len(supported) == len(markers):
        return text, []

    stripped: list[int] = []

    def _repl(match: re.Match[str]) -> str:
        n = int(match.group(1))
        if n in supported:
            return match.group(0)
        if n not in stripped:
            stripped.append(n)
        return "[citation needed]"

    annotated = _CITATION_MARKER_RE.sub(_repl, text)
    return annotated, sorted(stripped)


def render_provenance_footer(provenance: list[dict[str, Any]]) -> str:
    """Render a compact bullet list of tool calls used this turn.

    Designed to live below the answer in the Streamlit UI, inside a
    collapsed expander.
    """
    if not provenance:
        return "_No tools used this turn._"
    lines = []
    for i, p in enumerate(provenance, start=1):
        tool = p.get("tool", "?")
        args = p.get("args") or {}
        arg_repr = ", ".join(f"{k}={v!r}" for k, v in args.items() if k != "summary")
        lines.append(f"{i}. `{tool}({arg_repr})`")
    return "\n".join(lines)


__all__ = [
    "annotate_unsupported",
    "extract_citation_markers",
    "render_provenance_footer",
    "split_body_and_sources",
]
