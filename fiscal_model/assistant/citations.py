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


def format_answer_for_display(text: str) -> tuple[str, list[str]]:
    """Convert footnote syntax into plain markdown for display.

    Streamlit's markdown has no footnote support, so ``[^N]`` markers and
    ``[^N]: ...`` Sources lines render literally — reviewers saw six raw
    markers "resolving to nothing". For display we turn each marker into
    ``[N]`` (linked when its Sources entry carries a URL), drop markers with
    no Sources entry, and return the Sources entries as reader-visible lines.

    Returns ``(display_body, source_lines)``.
    """
    body, sources = split_body_and_sources(text)
    sources_map = _parse_sources(sources)

    # System notes appended after the model's own ``## Sources`` block (the
    # ``> ✂️`` truncation note, the ``> ⚠️`` stripped-markers note) would
    # otherwise vanish here: they are not ``[^N]:`` entries, so the split
    # dropped them and a cut-off answer looked complete. Carry blockquote
    # lines from the sources half back into the display body.
    trailing_notes = [
        line.strip()
        for line in (sources or "").splitlines()
        if line.lstrip().startswith(">")
    ]

    def _repl(match: re.Match[str]) -> str:
        n = int(match.group(1))
        entry = sources_map.get(n)
        if entry:
            urls = _URL_RE.findall(entry)
            if urls:
                return f"[[{n}]]({urls[0]})"
            return f"[{n}]"
        # A marker with no Sources entry carries nothing a reader can follow.
        return ""

    display_body = _CITATION_MARKER_RE.sub(_repl, body).rstrip()
    if trailing_notes:
        display_body += "\n\n" + "\n".join(trailing_notes)
    source_lines = [f"[{n}] {sources_map[n]}" for n in sorted(sources_map)]
    return display_body, source_lines


# ---------------------------------------------------------------------------
# Reader-facing Sources row
# ---------------------------------------------------------------------------

_SUPERSCRIPTS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

# ``CBO (2026), "Budget Outlook", https://…`` -> title / publisher-and-date.
_SOURCE_QUOTED_TITLE_RE = re.compile(r"[\"“]([^\"”]+)[\"”]")
_SOURCE_YEAR_RE = re.compile(r"\((\d{4}(?:[-/]\d{1,2})?)\)")


def _superscript(n: int) -> str:
    return str(n).translate(_SUPERSCRIPTS)


def _parse_source_entry(entry: str) -> dict[str, Any]:
    """Split a ``[^N]: …`` Sources line into title / publisher / date / URL."""
    text = entry.strip()
    urls = _URL_RE.findall(text)
    url = urls[0] if urls else None

    without_url = text
    if url:
        without_url = without_url.replace(url, "").strip().strip(",;. ")

    date = None
    year_match = _SOURCE_YEAR_RE.search(without_url)
    if year_match:
        date = year_match.group(1)

    quoted = _SOURCE_QUOTED_TITLE_RE.search(without_url)
    if quoted:
        title = quoted.group(1).strip()
        publisher = without_url[: quoted.start()].strip().strip(",;-— ")
        if year_match:
            publisher = publisher.replace(year_match.group(0), "").strip().strip(",;-— ")
    else:
        title = without_url or (url or "Source")
        publisher = None
        if year_match:
            title = title.replace(year_match.group(0), "").strip().strip(",;-— ")

    return {
        "title": title or (url or "Source"),
        "publisher": publisher or None,
        "date": date,
        "url": url,
    }


def _record_key(record: dict[str, Any]) -> str:
    """Identity used to de-duplicate sources across markers and provenance."""
    url = (record.get("url") or "").strip().rstrip("/")
    if url:
        return f"url:{url.lower()}"
    return f"title:{(record.get('title') or '').strip().lower()}"


def _provenance_source_records(
    provenance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Every citable record the tools surfaced this turn, in call order."""
    records: list[dict[str, Any]] = []
    for call in provenance or []:
        explicit = call.get("sources")
        if explicit:
            for record in explicit:
                if isinstance(record, dict) and record.get("title"):
                    records.append(dict(record))
            continue
        # Shared links and older transcripts carry only ``tool``/``args``.
        tool = call.get("tool", "")
        label = _TOOL_FRIENDLY_NAMES.get(tool)
        urls = [u for u in (call.get("urls") or []) if u]
        if not urls and tool == "fetch_url":
            arg_url = (call.get("args") or {}).get("url")
            if arg_url:
                urls = [str(arg_url)]
        if urls:
            for url in urls:
                records.append(
                    {"title": label or url, "publisher": None, "date": None, "url": url}
                )
        elif label:
            records.append(
                {"title": label, "publisher": None, "date": None, "url": None}
            )
    return records


def format_source_line(record: dict[str, Any]) -> str:
    """One numbered Sources entry as markdown: title, publisher, date, link."""
    title = str(record.get("title") or "Source").strip()
    url = record.get("url")
    head = f"[{title}]({url})" if url else title
    detail = " · ".join(
        str(part).strip()
        for part in (record.get("publisher"), record.get("date"))
        if part
    )
    return f"{record['n']}. {head}" + (f" — {detail}" if detail else "")


def build_answer_display(
    text: str,
    provenance: list[dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Render an answer for display and build its numbered Sources list.

    Streamlit markdown has no footnote support, so a raw ``[^N]`` renders
    literally — the tab promised citations and delivered dangling markers.
    This is the replacement contract:

    * every ``[^N]`` that resolves to a source becomes a **superscript
      numeral**, hyperlinked to that source when it has a URL;
    * markers are renumbered ``1..k`` in order of first appearance so the
      superscripts match the Sources row exactly;
    * a marker that resolves to nothing is **removed** — a bare ``[^N]``
      never reaches the reader;
    * sources the tools surfaced but the model never cited are appended, so
      the row is honest about what the answer actually drew on.

    Returns ``(display_body, sources)`` where each source is
    ``{"n", "title", "publisher", "date", "url"}``.
    """
    body, sources_block = split_body_and_sources(text or "")
    sources_map = _parse_sources(sources_block)
    prov_records = _provenance_source_records(provenance or [])

    # A marker with no Sources entry still means "grounded in a tool this
    # turn" (annotate_unsupported already stripped the unsupported ones), so
    # fall back to the first internal record rather than dropping the claim.
    fallback = next(
        (r for r in prov_records if not r.get("url")),
        prov_records[0] if prov_records else None,
    )

    ordered: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    marker_to_number: dict[int, int | None] = {}

    def _register(record: dict[str, Any]) -> dict[str, Any]:
        key = _record_key(record)
        existing = by_key.get(key)
        if existing is not None:
            return existing
        entry = dict(record)
        entry["n"] = len(ordered) + 1
        ordered.append(entry)
        by_key[key] = entry
        return entry

    def _resolve(marker: int) -> int | None:
        if marker in marker_to_number:
            return marker_to_number[marker]
        raw = sources_map.get(marker)
        record = _parse_source_entry(raw) if raw else fallback
        number = _register(record)["n"] if record else None
        marker_to_number[marker] = number
        return number

    def _repl(match: re.Match[str]) -> str:
        number = _resolve(int(match.group(1)))
        if number is None:
            return ""
        entry = ordered[number - 1]
        marker = _superscript(number)
        url = entry.get("url")
        return f"[{marker}]({url})" if url else marker

    display_body = _CITATION_MARKER_RE.sub(_repl, body).rstrip()

    # System notes appended after the model's ``## Sources`` block (the
    # truncation and stripped-marker blockquotes) would otherwise vanish.
    trailing_notes = [
        line.strip()
        for line in (sources_block or "").splitlines()
        if line.lstrip().startswith(">")
    ]
    if trailing_notes:
        display_body += "\n\n" + "\n".join(trailing_notes)

    # Anything the model listed but never cited inline, then anything the
    # tools surfaced that is still unrepresented.
    for marker in sorted(sources_map):
        if marker not in marker_to_number:
            _register(_parse_source_entry(sources_map[marker]))
    for record in prov_records:
        _register(record)

    return display_body, ordered


def render_sources_markdown(sources: list[dict[str, Any]]) -> str:
    """The ``**Sources (N)**`` block as a single markdown string."""
    if not sources:
        return ""
    lines = [f"**Sources ({len(sources)})**", ""]
    lines += [format_source_line(record) for record in sources]
    return "\n".join(lines)


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


_TOOL_FRIENDLY_NAMES = {
    "get_app_scoring_context": "This app's scoring engine",
    "get_cbo_baseline": "This app's CBO baseline",
    "get_validation_scorecard": "This app's validation scorecard",
    "list_presets": "This app's preset library",
    "get_preset": "This app's preset library",
    "score_hypothetical_policy": "This app's scoring engine",
    "search_knowledge": "Curated knowledge base",
    "query_fred": "FRED (Federal Reserve economic data)",
    "web_search": "Web search",
    "fetch_url": "Fetched web page",
}


def describe_sources(provenance: list[dict[str, Any]]) -> list[str]:
    """Reader-facing source lines for the "Drew on N sources" expander.

    One line per tool call, in plain language, with the query or URL that
    was consulted — so "Drew on 3 sources" is inspectable instead of an
    unverifiable claim. Not the dev-mode tool dump: no arg reprs.
    """
    lines: list[str] = []
    for p in provenance:
        tool = p.get("tool", "?")
        args = p.get("args") or {}
        label = _TOOL_FRIENDLY_NAMES.get(tool, tool.replace("_", " ").capitalize())
        detail = ""
        query = args.get("query") or args.get("q")
        if tool == "query_fred" and args.get("series_id"):
            detail = f"series {args['series_id']}"
        elif tool == "fetch_url" and args.get("url"):
            detail = str(args["url"])
        elif query:
            detail = f"“{query}”"
        urls = [u for u in (p.get("urls") or []) if u]
        line = f"**{label}**" + (f" — {detail}" if detail else "")
        if urls:
            line += "<br>" + " · ".join(f"[{u}]({u})" for u in urls[:3])
        lines.append(line)
    return lines


__all__ = [
    "annotate_unsupported",
    "build_answer_display",
    "describe_sources",
    "extract_citation_markers",
    "format_answer_for_display",
    "format_source_line",
    "render_provenance_footer",
    "render_sources_markdown",
    "split_body_and_sources",
]
