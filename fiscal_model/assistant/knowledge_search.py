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


class KnowledgeSearcher:
    """Tiny BM25 over Markdown snapshots in a directory."""

    def __init__(self, knowledge_dir: str | Path) -> None:
        self.knowledge_dir = Path(knowledge_dir)
        self._docs: list[_IndexedDoc] = []
        self._df: Counter[str] = Counter()
        self._avg_len: float = 0.0
        self._mtime_seen: dict[Path, float] = {}

    # ---- index management -----------------------------------------------

    def _needs_rebuild(self) -> bool:
        if not self.knowledge_dir.exists():
            return bool(self._docs)
        current: dict[Path, float] = {}
        for path in self.knowledge_dir.glob("*.md"):
            current[path] = path.stat().st_mtime
        if set(current) != set(self._mtime_seen):
            return True
        return any(current[p] != self._mtime_seen.get(p) for p in current)

    def _build_index(self) -> None:
        self._docs = []
        self._df = Counter()
        self._mtime_seen = {}
        if not self.knowledge_dir.exists():
            self._avg_len = 0.0
            return
        for path in sorted(self.knowledge_dir.glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            meta, body = _parse_frontmatter(text)
            # Keyword padding for recall: include the keywords list in the
            # tokenized representation, replicated to boost weight.
            keywords = meta.get("keywords") or []
            padding = " ".join(keywords) * 3 if keywords else ""
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
            hits.append(
                {
                    "title": doc.metadata.get("title", doc.path.stem),
                    "org": doc.metadata.get("org"),
                    "year": doc.metadata.get("year"),
                    "source_url": doc.metadata.get("source"),
                    "file": doc.path.name,
                    "score": round(score, 3),
                    "excerpt": _best_excerpt(doc.body, q_tokens),
                }
            )
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
