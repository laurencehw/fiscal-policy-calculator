"""
Tests for fiscal_model.assistant.share — URL-encoded Q+A sharing.

Covers:
- Round trip: encode → decode preserves question, answer, model, provenance.
- Compression: typical answers fit comfortably in a 2000-char URL.
- Robustness: malformed / oversized / wrong-version tokens decode to None.
- build_share_url produces a valid URL with the token in the query string.
- Provenance entries are truncated to keep URLs bounded.
"""

from __future__ import annotations

import base64
import gzip
import json

import pytest

from fiscal_model.assistant.share import (
    SHARE_SCHEMA_VERSION,
    build_share_url,
    decode_share_payload,
    encode_share_payload,
)


class TestRoundTrip:
    def test_simple_qa(self) -> None:
        token = encode_share_payload(
            question="What's the deficit?",
            answer="Cumulative 10-year deficit is \\$28.7 trillion[^1].",
            provenance=[{"tool": "get_cbo_baseline", "args": {}}],
            model="claude-sonnet-4-6",
        )
        payload = decode_share_payload(token)
        assert payload is not None
        assert payload["question"] == "What's the deficit?"
        assert "28.7 trillion" in payload["answer"]
        assert payload["model"] == "claude-sonnet-4-6"
        # provenance compact form: list of dicts with 't' and 'a'.
        assert payload["provenance"][0]["t"] == "get_cbo_baseline"
        assert payload["version"] == SHARE_SCHEMA_VERSION

    def test_unicode_survives(self) -> None:
        token = encode_share_payload(
            question="Cómo funciona el déficit fiscal en €?",
            answer="The answer — with em-dashes and currency: €1.5B, \\$2.3T.",
        )
        payload = decode_share_payload(token)
        assert payload["question"].startswith("Cómo")
        assert "€" in payload["answer"]
        assert "—" in payload["answer"]

    def test_realistic_size_under_2k_chars(self) -> None:
        # Simulate a 400-word answer with footnotes.
        answer = (
            "Over the 2025-2034 window, the app's loaded CBO baseline "
            "projects a **cumulative 10-year deficit of \\$28.7 trillion**[^1]. "
            "By 2034, debt held by the public reaches **103.4% of GDP**[^1] "
            "— meaning federal debt would exceed the entire size of the "
            "U.S. economy before the decade is out. "
        ) * 4  # ~1300 chars
        token = encode_share_payload(
            question="What's the deficit projection?",
            answer=answer,
            provenance=[
                {"tool": "get_cbo_baseline", "args": {}},
                {"tool": "search_knowledge", "args": {"query": "deficit"}},
            ],
        )
        # gzip + base64 should compress this duplicative content sharply.
        assert len(token) < 2000


class TestRobustness:
    def test_empty_token_returns_none(self) -> None:
        assert decode_share_payload("") is None
        assert decode_share_payload("not-base64-!") is None

    def test_malformed_base64_returns_none(self) -> None:
        assert decode_share_payload("@@@@") is None

    def test_oversized_token_rejected(self) -> None:
        huge = "A" * 60_000
        assert decode_share_payload(huge) is None

    def test_garbage_gzip_returns_none(self) -> None:
        # Valid base64 but not gzip data.
        token = base64.urlsafe_b64encode(b"not gzip data").rstrip(b"=").decode("ascii")
        assert decode_share_payload(token) is None

    def test_future_version_rejected(self) -> None:
        payload = {
            "v": SHARE_SCHEMA_VERSION + 99,
            "q": "x",
            "a": "y",
            "p": [],
            "m": "claude",
        }
        compressed = gzip.compress(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        token = base64.urlsafe_b64encode(compressed).rstrip(b"=").decode("ascii")
        assert decode_share_payload(token) is None

    def test_decompression_bomb_rejected(self) -> None:
        # 1 MB of zeros compresses to a few hundred bytes — try to make
        # the decoder OOM. The MAX_DECODED_BYTES guard should catch it.
        zeros = b"0" * 1_000_000
        compressed = gzip.compress(zeros)
        token = base64.urlsafe_b64encode(compressed).rstrip(b"=").decode("ascii")
        assert decode_share_payload(token) is None


class TestProvenanceTruncation:
    def test_truncates_to_8_entries(self) -> None:
        prov = [{"tool": f"t{i}", "args": {}} for i in range(20)]
        token = encode_share_payload(
            question="q", answer="a", provenance=prov, model=None
        )
        decoded = decode_share_payload(token)
        assert decoded is not None
        assert len(decoded["provenance"]) == 8

    def test_truncates_long_arg_values(self) -> None:
        prov = [{"tool": "search_knowledge", "args": {"query": "x" * 1000}}]
        token = encode_share_payload(
            question="q", answer="a", provenance=prov, model=None
        )
        decoded = decode_share_payload(token)
        assert decoded is not None
        # The query value was dropped (len > 200 threshold).
        assert decoded["provenance"][0]["a"] == {}


class TestBuildShareUrl:
    def test_url_contains_token_and_tab(self) -> None:
        url = build_share_url(
            question="q",
            answer="a",
            provenance=None,
            model=None,
            public_app_url="https://example.com",
        )
        assert url.startswith("https://example.com/?")
        assert "ask_share=" in url
        assert "tab=ask" in url

    def test_empty_public_url_gives_relative(self) -> None:
        url = build_share_url(question="q", answer="a", public_app_url="")
        assert url.startswith("/?")
        assert "ask_share=" in url

    def test_strips_trailing_slash(self) -> None:
        url = build_share_url(
            question="q",
            answer="a",
            public_app_url="https://example.com/",
        )
        assert url.startswith("https://example.com/?")
        # No double slash.
        assert "https://example.com//" not in url
