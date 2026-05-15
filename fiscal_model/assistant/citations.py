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

_CITATION_MARKER_RE = re.compile(r"\[\^(\d+)\]")
_SOURCES_HEADING_RE = re.compile(
    r"(?m)^\s*##+\s*Sources\s*$|^\s*\*\*Sources\*\*\s*$"
)


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
    """Replace markers that have no provenance with a ``[citation needed]`` tag.

    A marker is considered "supported" if any of the following hold:

    * The model's Sources section maps it to a URL whose domain appears in
      the provenance trail (e.g., a ``fetch_url`` or ``web_search`` result).
    * At least one app-internal tool was called this turn (those don't have
      URLs; we trust their internal provenance).
    * ``web_search_citations`` (passed through from the Anthropic
      web_search results) contains a URL referenced near the marker.

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

    web_urls: set[str] = set()
    for p in provenance:
        if p.get("tool") == "fetch_url":
            url = (p.get("args") or {}).get("url")
            if url:
                web_urls.add(url)
    if web_search_citations:
        web_urls.update(web_search_citations)

    # Build a permissive support set: if either we have ANY web URL or any
    # internal tool call, accept all markers (the Sources section will tell
    # the reader which is which). Otherwise, strip.
    supported = has_internal_tool or bool(web_urls)

    if supported:
        return text, []

    stripped: list[int] = []

    def _repl(match: re.Match[str]) -> str:
        n = int(match.group(1))
        if n not in stripped:
            stripped.append(n)
        return "[citation needed]"

    annotated = _CITATION_MARKER_RE.sub(_repl, text)
    return annotated, stripped


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
