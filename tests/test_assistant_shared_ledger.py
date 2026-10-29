"""The shared spend ledger: one daily cap across every server instance."""

from __future__ import annotations

from typing import Any

import pytest
import requests

from fiscal_model.assistant.rate_limit import RateLimitConfig, RateLimiter
from fiscal_model.assistant.shared_ledger import SharedLedger, SharedLedgerError


class FakeRedis:
    """Upstash's /pipeline endpoint over a dict."""

    def __init__(self):
        self.data: dict[str, float] = {}
        self.fail = False

    def post(self, url: str, json: list[list[Any]], headers: dict[str, str], timeout: float):
        assert url.endswith("/pipeline") and headers["Authorization"] == "Bearer secret"
        if self.fail:
            raise requests.ConnectionError("down")
        replies = []
        for cmd in json:
            op, key, *rest = cmd
            if op == "GET":
                value = self.data.get(key)
                replies.append({"result": None if value is None else str(value)})
            elif op == "INCRBYFLOAT":
                self.data[key] = self.data.get(key, 0.0) + float(rest[0])
                replies.append({"result": str(self.data[key])})
            elif op == "INCR":
                self.data[key] = self.data.get(key, 0) + 1
                replies.append({"result": self.data[key]})
            elif op == "EXPIRE":
                replies.append({"result": 1})
            else:
                replies.append({"error": "unknown"})

        class Reply:
            status_code = 200

            def json(self_inner):
                return replies

        return Reply()


@pytest.fixture
def redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(requests, "post", fake.post)
    return fake


def _limiter(tmp_path, ledger, **config):
    return RateLimiter(RateLimitConfig(**config), db_path=tmp_path / "usage.db", shared=ledger)


def test_two_instances_share_one_daily_cap(redis, tmp_path):
    ledger = SharedLedger("https://example.upstash.io", "secret")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = _limiter(tmp_path / "a", ledger, daily_cost_cap_usd=1.0)
    b = _limiter(tmp_path / "b", ledger, daily_cost_cap_usd=1.0)
    a.record_turn(session_id="s1", role="assistant", usage_dict={"cost_usd": 0.6})
    assert b.check(session_id="s2", session_message_count=0, last_message_ts=None).allowed
    b.record_turn(session_id="s2", role="assistant", usage_dict={"cost_usd": 0.5})
    # Each instance's own sqlite file holds less than the cap; the shared total does not.
    refused = a.check(session_id="s3", session_message_count=0, last_message_ts=None)
    assert not refused.allowed and "budget" in refused.reason
    assert refused.today_spend_usd == pytest.approx(1.1)


def test_an_unreachable_store_refuses_rather_than_spends(redis, tmp_path):
    limiter = _limiter(tmp_path, SharedLedger("https://example.upstash.io", "secret"))
    redis.fail = True
    decision = limiter.check(session_id="s", session_message_count=0, last_message_ts=None)
    assert not decision.allowed and "cannot check" in decision.reason
    with pytest.raises(SharedLedgerError):
        limiter.today_spend_usd(strict=True)


def test_each_session_is_capped_per_day(redis, tmp_path):
    limiter = _limiter(tmp_path, SharedLedger("https://example.upstash.io", "secret"), session_daily_cap=2)
    for _ in range(2):
        assert limiter.check(session_id="visitor", session_message_count=0, last_message_ts=None).allowed
        limiter.record_turn(session_id="visitor", role="assistant", usage_dict={"cost_usd": 0.01})
    # Follow-up chips and other auxiliary calls are not answers and do not count.
    limiter.record_turn(session_id="other", role="followups", usage_dict={"cost_usd": 0.01})
    refused = limiter.check(session_id="visitor", session_message_count=0, last_message_ts=None)
    assert not refused.allowed and "questions today" in refused.reason
    assert limiter.check(session_id="other", session_message_count=0, last_message_ts=None).allowed


def test_the_session_cap_also_works_on_sqlite_alone(tmp_path):
    limiter = _limiter(tmp_path, None, session_daily_cap=1)
    limiter.record_turn(session_id="v", role="assistant", usage_dict={"cost_usd": 0.0})
    assert not limiter.check(session_id="v", session_message_count=0, last_message_ts=None).allowed


def test_the_store_is_read_from_either_pair_of_names(monkeypatch):
    for name in ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN", "KV_REST_API_URL", "KV_REST_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    assert SharedLedger.from_env() is None
    monkeypatch.setenv("KV_REST_API_URL", "https://kv.example")
    monkeypatch.setenv("KV_REST_API_TOKEN", "t0ken")
    ledger = SharedLedger.from_env()
    assert ledger is not None and ledger.url == "https://kv.example"
    assert "t0ken" not in repr(ledger)
    monkeypatch.setenv("KV_REST_API_URL", "http://insecure.example")
    assert SharedLedger.from_env() is None
