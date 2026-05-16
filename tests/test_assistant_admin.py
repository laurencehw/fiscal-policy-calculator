"""
Tests for fiscal_model.assistant.admin — the read-only dashboard queries.

Covers:
- Token gate: ``is_admin_request`` rejects when the env var is unset, the
  query param is missing, or the value doesn't match.
- Headline snapshot KPIs computed correctly from seeded events.
- Daily-spend series fills missing days with zero.
- Tool-usage frequency aggregates across rows.
- Recent-turns table returns the last N in insert order.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fiscal_model.assistant.admin import (
    admin_token_configured,
    daily_spend_series,
    is_admin_request,
    recent_turns,
    snapshot,
    tool_usage_counts,
)
from fiscal_model.assistant.rate_limit import RateLimitConfig, RateLimiter


@pytest.fixture
def limiter(tmp_path: Path) -> RateLimiter:
    cfg = RateLimitConfig(
        daily_cost_cap_usd=5.00,
        session_message_cap=20,
        cooldown_seconds=0.0,
        disabled=False,
    )
    return RateLimiter(cfg, db_path=tmp_path / "usage.db")


def _seed(limiter: RateLimiter, n: int = 5) -> None:
    """Seed n turns with varying tool calls and costs."""
    tools_cycle = [
        ["get_cbo_baseline"],
        ["search_knowledge"],
        ["search_knowledge", "score_hypothetical_policy"],
        ["get_validation_scorecard"],
        ["query_fred"],
    ]
    for i in range(n):
        limiter.record_turn(
            session_id=f"s{i % 3}",  # 3 distinct sessions
            role="assistant",
            model="claude-sonnet-4-6",
            usage_dict={
                "input_tokens": 100 + i * 10,
                "output_tokens": 80,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 50 if i > 0 else 0,
                "cost_usd": 0.01 + i * 0.005,
            },
            elapsed_s=2.0 + i * 0.5,
            tools_used=tools_cycle[i % len(tools_cycle)],
            stripped_markers=0,
            error="boom" if i == 4 else None,
            question_chars=120,
            answer_chars=600,
        )


# ---------------------------------------------------------------------------
# Token gate
# ---------------------------------------------------------------------------


class TestTokenGate:
    def test_admin_token_configured_reads_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ASSISTANT_ADMIN_TOKEN", raising=False)
        assert admin_token_configured() is False
        monkeypatch.setenv("ASSISTANT_ADMIN_TOKEN", "secret")
        assert admin_token_configured() is True

    def test_is_admin_request_no_token_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("ASSISTANT_ADMIN_TOKEN", raising=False)
        assert is_admin_request({"admin": "anything"}) is False

    def test_is_admin_request_matching(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ASSISTANT_ADMIN_TOKEN", "secret")
        assert is_admin_request({"admin": "secret"}) is True
        # List form (legacy Streamlit)
        assert is_admin_request({"admin": ["secret"]}) is True

    def test_is_admin_request_wrong_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ASSISTANT_ADMIN_TOKEN", "secret")
        assert is_admin_request({"admin": "wrong"}) is False
        assert is_admin_request({}) is False

    def test_is_admin_request_handles_attribute_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ASSISTANT_ADMIN_TOKEN", "secret")
        # A param object that explodes on .get() shouldn't crash; just return False.
        class Bad:
            def get(self, key: str):
                raise RuntimeError("nope")

        assert is_admin_request(Bad()) is False


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_empty_db(self, limiter: RateLimiter) -> None:
        snap = snapshot(limiter)
        assert snap.total_turns == 0
        assert snap.total_cost_usd == 0.0
        assert snap.today_turns == 0
        assert snap.cache_hit_ratio == 0.0
        assert snap.error_rate_pct == 0.0

    def test_aggregates_from_seeded_rows(self, limiter: RateLimiter) -> None:
        _seed(limiter, n=5)
        snap = snapshot(limiter)
        assert snap.total_turns == 5
        # Seeded costs: 0.010, 0.015, 0.020, 0.025, 0.030 → total 0.100
        assert snap.total_cost_usd == pytest.approx(0.100, rel=1e-3)
        # Today equals all-time when all seeded today.
        assert snap.today_turns == 5
        assert snap.today_cost_usd == pytest.approx(0.100, rel=1e-3)
        # 1 error / 5 turns = 20%
        assert snap.error_rate_pct == pytest.approx(20.0, rel=1e-3)
        # 4 turns have 50 cache-read tokens each (4×50 = 200);
        # input_tokens sums to 100+110+120+130+140 = 600;
        # cache_creation = 0; total_in = 600 + 200 + 0 = 800;
        # cache_hit_ratio = 200/800 = 0.25.
        assert snap.cache_hit_ratio == pytest.approx(0.25, rel=1e-2)
        # 3 distinct sessions
        assert snap.n_unique_sessions_30d == 3


# ---------------------------------------------------------------------------
# Daily series
# ---------------------------------------------------------------------------


class TestDailySpend:
    def test_fills_missing_days_with_zero(self, limiter: RateLimiter) -> None:
        _seed(limiter, n=3)
        df = daily_spend_series(limiter, days=7)
        assert len(df) == 7
        # Every row has the day key and non-negative cost.
        assert all(df["cost_usd"] >= 0)
        # Today's row has non-zero spend (seed wrote today).
        today_row = df.iloc[-1]
        assert today_row["cost_usd"] > 0
        # Older days have zero.
        assert (df.iloc[:-1]["cost_usd"] == 0).all()


# ---------------------------------------------------------------------------
# Tool usage
# ---------------------------------------------------------------------------


class TestToolUsage:
    def test_counts_each_tool_call(self, limiter: RateLimiter) -> None:
        _seed(limiter, n=5)
        df = tool_usage_counts(limiter, days=30)
        # 5 turns: tools were [get_cbo_baseline], [search_knowledge],
        # [search_knowledge, score_hypothetical_policy], [get_validation_scorecard], [query_fred]
        # → search_knowledge=2, others=1 each. Length must be 5 distinct tools.
        as_dict = dict(zip(df["tool"], df["calls"], strict=True))
        assert as_dict.get("search_knowledge") == 2
        assert as_dict.get("get_cbo_baseline") == 1
        assert as_dict.get("score_hypothetical_policy") == 1
        # Most-called appears first.
        assert df.iloc[0]["tool"] == "search_knowledge"

    def test_empty_db(self, limiter: RateLimiter) -> None:
        df = tool_usage_counts(limiter, days=30)
        assert df.empty


# ---------------------------------------------------------------------------
# Recent turns
# ---------------------------------------------------------------------------


class TestRecentTurns:
    def test_returns_in_reverse_insert_order(self, limiter: RateLimiter) -> None:
        _seed(limiter, n=5)
        df = recent_turns(limiter, limit=3)
        assert len(df) == 3
        # Most recent row has the highest cost (last seeded).
        assert df.iloc[0]["cost_usd"] == pytest.approx(0.030, rel=1e-3)
        # Error from row 4 (last seeded) surfaces in the top row.
        assert "boom" in df.iloc[0]["error"]

    def test_empty_db(self, limiter: RateLimiter) -> None:
        df = recent_turns(limiter, limit=10)
        assert df.empty
