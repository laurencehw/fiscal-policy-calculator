"""
Shareable-URL encoding for individual Ask Q+A turns.

The shared payload is **self-contained** — the question text, the answer
text, and a small provenance summary — so the recipient gets the exact
same content without any server-side state. This lets shared links
survive Streamlit Cloud container restarts without needing a durable
database.

Encoding pipeline:

1. JSON-serialize a compact payload (no whitespace).
2. ``gzip`` compress.
3. URL-safe base64 encode (no padding) — produces ASCII suitable for
   query strings.

A 600-word answer typically encodes to ~800-1500 chars; well within the
~2000-char ceiling most clients and platforms tolerate. Longer answers
are still encoded but the URL grows linearly.
"""

from __future__ import annotations

import base64
import gzip
import json
import logging
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


# Bump when the payload shape changes in a breaking way; older links
# fail with a clear "outdated link" message instead of garbled rendering.
SHARE_SCHEMA_VERSION = 1

# Hard cap so a malicious URL can't unzip to gigabytes.
MAX_DECODED_BYTES = 200_000


def encode_share_payload(
    *,
    question: str,
    answer: str,
    provenance: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> str:
    """Encode a Q+A turn into a URL-safe token.

    Returns a base64url string with no padding. Round-trips through
    :func:`decode_share_payload`.
    """
    payload = {
        "v": SHARE_SCHEMA_VERSION,
        "q": (question or "").strip()[:4000],
        "a": (answer or "").strip()[:12_000],
        "p": _compact_provenance(provenance or []),
        "m": model,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=9)
    return base64.urlsafe_b64encode(compressed).rstrip(b"=").decode("ascii")


def decode_share_payload(token: str) -> dict[str, Any] | None:
    """Reverse of :func:`encode_share_payload`. Returns ``None`` on failure."""
    if not token or len(token) > 50_000:
        return None
    try:
        # base64url requires padding to be a multiple of 4; restore it.
        padded = token + "=" * (-len(token) % 4)
        compressed = base64.urlsafe_b64decode(padded.encode("ascii"))
        if len(compressed) > MAX_DECODED_BYTES:
            return None
        raw = gzip.decompress(compressed)
        if len(raw) > MAX_DECODED_BYTES:
            return None
        payload = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001 — malformed input shouldn't crash the app
        logger.info("decode_share_payload: rejected malformed token", exc_info=True)
        return None
    if not isinstance(payload, dict):
        return None
    if int(payload.get("v", 0)) > SHARE_SCHEMA_VERSION:
        # Future schema we don't know how to render.
        return None
    return {
        "version": int(payload.get("v", 0)),
        "question": str(payload.get("q") or ""),
        "answer": str(payload.get("a") or ""),
        "provenance": payload.get("p") or [],
        "model": payload.get("m"),
    }


def build_share_url(
    *,
    question: str,
    answer: str,
    provenance: list[dict[str, Any]] | None = None,
    model: str | None = None,
    public_app_url: str = "",
) -> str:
    """Return a ready-to-paste share URL. Empty ``public_app_url`` yields
    a relative URL (``/?...``) — useful for local dev.
    """
    token = encode_share_payload(
        question=question, answer=answer, provenance=provenance, model=model
    )
    query = urlencode({"ask_share": token, "tab": "ask"})
    base = public_app_url.rstrip("/") if public_app_url else ""
    return f"{base}/?{query}"


def _compact_provenance(prov: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Trim provenance entries to the minimum useful for rendering.

    Keep tool name and a short hint of args; drop the full result summary
    which can be many KB.
    """
    out: list[dict[str, Any]] = []
    for entry in prov[:8]:  # cap at 8 tool calls
        if not isinstance(entry, dict):
            continue
        tool = str(entry.get("tool") or "")
        args = entry.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        # Keep small arg values; drop anything bulky.
        small_args = {
            k: str(v)[:120]
            for k, v in args.items()
            if isinstance(k, str) and len(str(v)) < 200
        }
        out.append({"t": tool, "a": small_args})
    return out


__all__ = [
    "SHARE_SCHEMA_VERSION",
    "build_share_url",
    "decode_share_payload",
    "encode_share_payload",
]
