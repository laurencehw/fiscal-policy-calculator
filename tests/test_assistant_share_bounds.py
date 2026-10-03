"""Share-token decoding must be bounded and flagged untrusted.

Defect (2026-10 hunt): ``decode_share_payload`` called ``gzip.decompress`` and
only then checked ``MAX_DECODED_BYTES``, so a tiny forged ``?ask_share=`` token
inflated to its full (unbounded) size first. The payload is also unsigned: a
forged token becomes an assistant turn in the victim's conversation.
"""

from __future__ import annotations

import base64
import gzip
import json
import tracemalloc

from fiscal_model.assistant import share
from fiscal_model.assistant.share import (
    MAX_DECODED_BYTES,
    decode_share_payload,
    encode_share_payload,
)


def _token(raw: bytes) -> str:
    return base64.urlsafe_b64encode(gzip.compress(raw, 9)).rstrip(b"=").decode()


def test_decompression_bomb_is_rejected_without_inflating_it() -> None:
    # ~30 MB of highly compressible JSON in a token under the 50 KB length cap.
    bomb = b'{"v":1,"q":"x","a":"' + b"A" * 30_000_000 + b'"}'
    token = _token(bomb)
    assert len(token) < 50_000  # so the length guard cannot be what rejects it

    tracemalloc.start()
    try:
        assert decode_share_payload(token) is None
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    # Bounded: nowhere near the 30 MB the stream expands to.
    assert peak < 5 * MAX_DECODED_BYTES


def test_decompression_is_capped_with_max_length(monkeypatch) -> None:
    """gzip.decompress (unbounded) must not be what decodes a token."""

    def boom(*a, **k):
        raise AssertionError("unbounded gzip.decompress called")

    monkeypatch.setattr(share.gzip, "decompress", boom)
    token = encode_share_payload(question="q", answer="a")
    assert decode_share_payload(token) is not None


def test_payload_exactly_at_limit_decodes_and_one_over_is_rejected() -> None:
    base = json.dumps({"v": 1, "q": "q", "a": "", "pad": ""}).encode()
    pad = MAX_DECODED_BYTES - len(base)
    at_limit = json.dumps({"v": 1, "q": "q", "a": "", "pad": "x" * pad}).encode()
    assert len(at_limit) == MAX_DECODED_BYTES
    assert decode_share_payload(_token(at_limit)) is not None
    assert decode_share_payload(_token(at_limit + b" ")) is None


def test_truncated_gzip_stream_is_rejected() -> None:
    full = gzip.compress(b'{"v":1,"q":"q","a":"a"}' * 50)
    token = base64.urlsafe_b64encode(full[: len(full) // 2]).rstrip(b"=").decode()
    assert decode_share_payload(token) is None


def test_non_numeric_version_is_rejected_not_raised() -> None:
    assert decode_share_payload(_token(b'{"v":"abc","q":"q","a":"a"}')) is None


def test_decoded_payload_is_flagged_untrusted() -> None:
    payload = decode_share_payload(encode_share_payload(question="q", answer="a"))
    assert payload is not None
    assert payload["untrusted"] is True


def test_forged_provenance_is_rebuilt_from_bounded_primitives() -> None:
    forged = json.dumps(
        {
            "v": 1,
            "q": "q",
            "a": "a" * 50_000,
            "p": [{"t": "t" * 500, "a": {"k": "v" * 5_000, "n": {"deep": [1]}}}]
            + ["not-a-dict"] * 5
            + [{"t": "x"}] * 20,
            "m": {"not": "a string"},
        }
    ).encode()
    payload = decode_share_payload(_token(forged))
    assert payload is not None and payload["untrusted"] is True
    assert len(payload["answer"]) <= 12_000
    prov = payload["provenance"]
    assert len(prov) <= 8
    assert all(set(p) == {"t", "a"} for p in prov)
    assert len(prov[0]["t"]) <= 60
    assert all(isinstance(v, str) and len(v) <= 120 for v in prov[0]["a"].values())
