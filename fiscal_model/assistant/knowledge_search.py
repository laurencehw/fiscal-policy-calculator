"""
Curated-knowledge search.

The ``knowledge/`` directory holds hand-maintained Markdown snapshots of
authoritative material (CBO baseline highlights, SS trustees summary,
TCJA overview, key definitions, …). Each file carries a small YAML-ish
frontmatter:

    ---
    source: https://www.cbo.gov/publication/...
    title: An Update to the Budget and Economic Outlook: 2026 to 2036
    org: CBO
    year: 2026
    keywords: [deficit, baseline, primary deficit, projections, ...]
    ---

The frontmatter ``keywords`` line is critical: BM25 matches the user's
query against the body and the keywords together, so adding synonyms
("primary deficit", "primary balance") raises recall.

The search index is built lazily on first query and re-built when any
file's mtime changes.
"""

from __future__ import annotations

import contextlib
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-']+")
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "of",
        "in",
        "on",
        "for",
        "to",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "this",
        "that",
        "these",
        "those",
        "by",
        "with",
        "from",
        "as",
        "at",
        "it",
        "its",
        "into",
    }
)


def _tokenize(text: str) -> list[str]:
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text)
        if t.lower() not in _STOPWORDS and len(t) > 1
    ]


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return ``(metadata, body)`` for a Markdown file with optional frontmatter."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end():]
    meta: dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            # Naive list parse: comma-separated.
            inner = value[1:-1]
            meta[key.strip()] = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
        else:
            meta[key.strip()] = value.strip("'\"")
    return meta, body


@dataclass
class _IndexedDoc:
    path: Path
    metadata: dict[str, Any]
    body: str
    tokens: list[str]
    token_freq: Counter[str] = field(default_factory=Counter)
    length: int = 0


def _strip_leading_emoji(label: str) -> str:
    """Remove leading emoji / symbol prefixes from preset names."""
    return re.sub(r"^[^\w$+\-]+", "", label).strip()


def _format_signed_billions(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else "-" if value < 0 else ""
    mag = abs(float(value))
    if mag >= 1000:
        return f"{sign}${mag / 1000:.2f}T ({sign}${mag:,.1f}B)"
    return f"{sign}${mag:,.1f}B"


def _discover_presets_dir(knowledge_dir: Path) -> Path | None:
    """Auto-discover ``site_data/presets`` when using the repo's own knowledge dir."""
    resolved = knowledge_dir.resolve()
    if resolved.name == "knowledge" and resolved.parent.name == "assistant":
        candidate = resolved.parents[2] / "site_data" / "presets"
        if candidate.is_dir():
            return candidate
    return None


def _preset_json_to_doc(
    path: Path,
    index_meta: dict[str, Any],
) -> _IndexedDoc | None:
    """Convert one ``site_data/presets/<id>.json`` into an indexed RAG document."""
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None

    preset_id = str(data.get("id") or path.stem)
    conv = data.get("conventional") or {}
    dyn = data.get("dynamic") or {}
    cred = conv.get("credibility") or {}

    raw_name = str(conv.get("policy_name") or preset_id)
    title = _strip_leading_emoji(raw_name) or preset_id
    desc = str(conv.get("policy_description") or "").replace("\\$", "$")
    window = str(conv.get("budget_window") or "FY2026-2035")
    vintage = str(conv.get("baseline_vintage") or "")
    conv_10yr = conv.get("ten_year_deficit_impact")
    dyn_10yr = dyn.get("dynamic_adjusted_impact")

    area = str(index_meta.get("area") or cred.get("category") or "")
    cbo_source = str(index_meta.get("cbo_source") or "").strip()
    official_b = cred.get("own_row_official_billions")
    tier_label = str(cred.get("own_row_tier_label") or "").strip()
    own_window = str(cred.get("own_row_window") or "").strip()
    abs_err = cred.get("own_row_abs_pct_error")

    direction = (
        "increases the deficit"
        if isinstance(conv_10yr, (int, float)) and conv_10yr > 0
        else "reduces the deficit"
        if isinstance(conv_10yr, (int, float)) and conv_10yr < 0
        else "is budget-neutral"
    )

    lines = [
        f"Preset `{preset_id}` ({title}, area: {area or 'Fiscal policy'}).",
        desc,
        (
            f"Calculator 10-year conventional estimate ({window}, {vintage} CBO baseline): "
            f"{_format_signed_billions(conv_10yr)} ({direction})."
        ),
    ]
    if isinstance(dyn_10yr, (int, float)):
        dyn_model = str(dyn.get("dynamic_model") or "FRB/US-Lite")
        lines.append(
            f"Dynamic score with demand feedback and debt service ({dyn_model}, no supply-side channel): "
            f"{_format_signed_billions(dyn_10yr)}."
        )
    if official_b is not None:
        bench_parts = [f"Published benchmark: {_format_signed_billions(official_b)}"]
        if cbo_source:
            bench_parts.append(f"({cbo_source})")
        if own_window:
            bench_parts.append(f"over {own_window}")
        if tier_label and isinstance(abs_err, (int, float)):
            bench_parts.append(f"[{tier_label}, {abs_err:.1f}% gap]")
        lines.append(" ".join(bench_parts) + ".")
    lines.append(f"Preset page: https://fiscal.lwilsesamson.com/explore/{preset_id}")

    body = "\n".join(line for line in lines if line)

    # Rich synonyms so natural-language policy queries hit the preset directly.
    slug_words = preset_id.replace("-", " ")
    keywords = [preset_id, slug_words, title, area]
    lower_blob = f"{preset_id} {title} {desc}".lower()
    if "aca" in lower_blob or "ptc" in lower_blob or "premium" in lower_blob:
        keywords.extend(["ACA", "Affordable Care Act", "premium tax credits", "PTC", "Obamacare", "subsidies"])
        if "enhanced" in lower_blob or "extend" in preset_id:
            keywords.extend(["enhanced", "extend", "extending", "restore", "restoring"])
        if "repeal" in lower_blob:
            keywords.extend(["repeal", "eliminate"])
    if "tcja" in lower_blob:
        keywords.extend(["TCJA", "Tax Cuts and Jobs Act", "2017 tax cuts", "extension"])
    if "tariff" in lower_blob:
        keywords.extend(["tariff", "tariffs", "trade", "imports", "customs"])
    if "ctc" in lower_blob or "child" in lower_blob:
        keywords.extend(["CTC", "Child Tax Credit", "refundable"])
    if "eitc" in lower_blob:
        keywords.extend(["EITC", "Earned Income Tax Credit"])
    if "salt" in lower_blob:
        keywords.extend(["SALT", "state and local tax deduction"])
    if "ss-" in preset_id or "social security" in lower_blob or "payroll" in lower_blob:
        keywords.extend(["Social Security", "payroll tax", "OASDI", "taxable maximum"])

    org = f"Fiscal Policy Calculator ({cbo_source})" if cbo_source else "Fiscal Policy Calculator"
    meta: dict[str, Any] = {
        "title": f"{title} — Site Preset ({preset_id})",
        "org": org,
        "year": window,
        "source": f"https://fiscal.lwilsesamson.com/explore/{preset_id}",
        "preset_id": preset_id,
        "keywords": [k for k in keywords if k],
    }
    padding = (" " + " ".join(meta["keywords"])) * 3
    tokens = _tokenize(f"{title} {padding} {body}")
    return _IndexedDoc(
        path=path,
        metadata=meta,
        body=body,
        tokens=tokens,
        token_freq=Counter(tokens),
        length=len(tokens),
    )


class KnowledgeSearcher:
    """Tiny BM25 over Markdown snapshots and pre-scored site preset summaries."""

    def __init__(
        self,
        knowledge_dir: str | Path,
        presets_dir: str | Path | None = None,
    ) -> None:
        self.knowledge_dir = Path(knowledge_dir)
        self.presets_dir: Path | None = (
            Path(presets_dir)
            if presets_dir is not None
            else _discover_presets_dir(self.knowledge_dir)
        )
        self._docs: list[_IndexedDoc] = []
        self._df: Counter[str] = Counter()
        self._avg_len: float = 0.0
        self._mtime_seen: dict[Path, float] = {}

    # ---- index management -----------------------------------------------

    def _source_files(self) -> tuple[list[Path], list[Path]]:
        md_files = (
            sorted(self.knowledge_dir.glob("*.md"))
            if self.knowledge_dir.exists()
            else []
        )
        preset_files: list[Path] = []
        if self.presets_dir is not None and self.presets_dir.exists():
            preset_files = sorted(
                p for p in self.presets_dir.glob("*.json") if p.name != "index.json"
            )
        return md_files, preset_files

    def _needs_rebuild(self) -> bool:
        md_files, preset_files = self._source_files()
        if not md_files and not preset_files:
            return bool(self._docs)
        current: dict[Path, float] = {}
        for path in (*md_files, *preset_files):
            try:
                current[path] = path.stat().st_mtime
            except OSError:
                continue
        if set(current) != set(self._mtime_seen):
            return True
        return any(current[p] != self._mtime_seen.get(p) for p in current)

    def _build_index(self) -> None:
        import json

        self._docs = []
        self._df = Counter()
        self._mtime_seen = {}
        md_files, preset_files = self._source_files()
        if not md_files and not preset_files:
            self._avg_len = 0.0
            return

        for path in md_files:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            meta, body = _parse_frontmatter(text)
            # Keyword padding for recall: include the keywords list in the
            # tokenized representation, replicated to boost weight.
            keywords = meta.get("keywords") or []
            padding = (" " + " ".join(keywords)) * 3 if keywords else ""
            title = meta.get("title", "")
            tokens = _tokenize(f"{title} {padding} {body}")
            doc = _IndexedDoc(
                path=path,
                metadata=meta,
                body=body,
                tokens=tokens,
                token_freq=Counter(tokens),
                length=len(tokens),
            )
            self._docs.append(doc)
            self._mtime_seen[path] = path.stat().st_mtime
            for term in set(tokens):
                self._df[term] += 1

        index_by_id: dict[str, dict[str, Any]] = {}
        if self.presets_dir is not None:
            index_path = self.presets_dir / "index.json"
            if index_path.exists():
                try:
                    raw_index = json.loads(index_path.read_text(encoding="utf-8"))
                    if isinstance(raw_index, list):
                        for row in raw_index:
                            if isinstance(row, dict) and row.get("id"):
                                index_by_id[str(row["id"])] = row
                except (OSError, ValueError):
                    pass

        for path in preset_files:
            doc = _preset_json_to_doc(path, index_by_id.get(path.stem, {}))
            if doc is None:
                continue
            self._docs.append(doc)
            with contextlib.suppress(OSError):
                self._mtime_seen[path] = path.stat().st_mtime
            for term in set(doc.tokens):
                self._df[term] += 1

        self._avg_len = (
            sum(d.length for d in self._docs) / len(self._docs) if self._docs else 0.0
        )

    # ---- search ----------------------------------------------------------

    def search(self, query: str, k: int = 4) -> list[dict[str, Any]]:
        if self._needs_rebuild():
            self._build_index()
        if not self._docs:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        n_docs = len(self._docs)
        k1, b = 1.5, 0.75
        scores: list[tuple[float, _IndexedDoc]] = []

        for doc in self._docs:
            score = 0.0
            for term in q_tokens:
                df = self._df.get(term, 0)
                if df == 0:
                    continue
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
                tf = doc.token_freq.get(term, 0)
                norm = 1 - b + b * (doc.length / self._avg_len if self._avg_len else 1)
                score += idf * (tf * (k1 + 1)) / (tf + k1 * norm)
            if score > 0:
                scores.append((score, doc))

        scores.sort(key=lambda t: t[0], reverse=True)
        hits: list[dict[str, Any]] = []
        for score, doc in scores[:k]:
            # Preset summaries are already compact (~400-700 chars); return them
            # intact so the assistant never misses the 10-year figure or benchmark.
            is_preset = "preset_id" in doc.metadata
            excerpt = (
                doc.body[:800].strip()
                if is_preset
                else _best_excerpt(doc.body, q_tokens)
            )
            hit: dict[str, Any] = {
                "title": doc.metadata.get("title", doc.path.stem),
                "org": doc.metadata.get("org"),
                "year": doc.metadata.get("year"),
                "source_url": doc.metadata.get("source"),
                "file": doc.path.name,
                "score": round(score, 3),
                "excerpt": excerpt,
            }
            if is_preset:
                hit["preset_id"] = doc.metadata["preset_id"]
            hits.append(hit)
        return hits


def _best_excerpt(body: str, q_tokens: list[str], window: int = 320) -> str:
    """Return a short passage near the best match for the query tokens."""
    lowered = body.lower()
    best_pos = -1
    for term in q_tokens:
        pos = lowered.find(term)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
    if best_pos == -1:
        return body[:window].strip()
    start = max(0, best_pos - window // 3)
    end = min(len(body), best_pos + window)
    snippet = body[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(body):
        snippet = snippet + "…"
    return snippet


__all__ = ["KnowledgeSearcher"]
