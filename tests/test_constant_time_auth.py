"""Secret comparisons go through ``hmac.compare_digest``.

A plain ``==`` (the admin token) or a dict lookup keyed on the secret (the
API keys) can return faster the earlier a guess diverges, which is a timing
oracle. These tests pin that both paths call ``compare_digest`` and still
answer correctly.
"""

from __future__ import annotations

import hmac

import pytest

from fiscal_model import api_security
from fiscal_model.assistant import admin


@pytest.fixture
def _counted_compare_digest(monkeypatch):
    calls: list[tuple[bytes, bytes]] = []
    real = hmac.compare_digest

    def counting(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(hmac, "compare_digest", counting)
    return calls


@pytest.fixture(autouse=True)
def _restore_security():
    yield
    api_security.configure(keys=None)
    api_security.reset_limiter()


def test_admin_token_comparison_is_constant_time(monkeypatch, _counted_compare_digest):
    monkeypatch.setenv("ASSISTANT_ADMIN_TOKEN", "s3cret-token")
    assert admin.is_admin_request({"admin": "s3cret-token"}) is True
    assert admin.is_admin_request({"admin": ["s3cret-token"]}) is True
    assert admin.is_admin_request({"admin": "s3cret-tokex"}) is False
    assert admin.is_admin_request({"admin": "ünïcode"}) is False
    assert len(_counted_compare_digest) == 4


def test_api_key_lookup_compares_every_configured_key(_counted_compare_digest):
    api_security.configure(keys={"a": "key-one", "b": "key-two", "c": "key-three"})
    _counted_compare_digest.clear()

    assert api_security._lookup_key("key-two").label == "b"
    # No early exit: all three configured keys were compared.
    assert len(_counted_compare_digest) == 3

    _counted_compare_digest.clear()
    assert api_security._lookup_key("key-nope") is None
    assert len(_counted_compare_digest) == 3

    assert api_security._lookup_key("") is None
    assert api_security._lookup_key(None) is None
    assert api_security._lookup_key("ключ") is None


def test_resolve_key_uses_the_constant_time_lookup(_counted_compare_digest):
    api_security.configure(keys={"research": "r-123"})
    _counted_compare_digest.clear()
    assert api_security._resolve_key_or_raise("r-123") == "research"
    assert _counted_compare_digest
