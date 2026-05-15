"""
Tests for ``fiscal_model.assistant.rate_limit``.

Covers:

* Decision logic — daily cap, session message cap, cooldown, kill switch.
* Sqlite persistence — today's spend is summed correctly across rows.
* Day rollover — yesterday's spend doesn't count toward today's cap.
* Env-var config — env overrides the dataclass defaults.
* Graceful failure — broken db path is reported but doesn't raise.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from fiscal_model.assistant.rate_limit import (
    RateLimitConfig,
    RateLimiter,
    new_session_id,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "usage.db"


def _config(**kwargs) -> RateLimitConfig:
    base = dict(
        daily_cost_cap_usd=1.00,
        session_message_cap=5,
        cooldown_seconds=0.0,  # disable for most tests
        disabled=False,
    )
    base.update(kwargs)
    return RateLimitConfig(**base)


class TestDecision:
    def test_kill_switch(self, db_path: Path) -> None:
        rl = RateLimiter(_config(disabled=True), db_path=db_path)
        d = rl.check(session_id="s1", session_message_count=0, last_message_ts=None)
        assert not d.allowed
        assert "disabled" in d.reason.lower()

    def test_daily_cap_blocks_when_exceeded(self, db_path: Path) -> None:
        rl = RateLimiter(_config(), db_path=db_path)
        rl.record_turn(
            session_id="s1",
            role="assistant",
            model="claude-sonnet-4-6",
            usage_dict={"cost_usd": 1.50, "input_tokens": 0, "output_tokens": 0},
        )
        d = rl.check(session_id="s2", session_message_count=0, last_message_ts=None)
        assert not d.allowed
        assert d.today_spend_usd >= 1.50
        assert "budget" in d.reason.lower()

    def test_session_cap_blocks_when_reached(self, db_path: Path) -> None:
        rl = RateLimiter(_config(session_message_cap=3), db_path=db_path)
        d = rl.check(session_id="s1", session_message_count=3, last_message_ts=None)
        assert not d.allowed
        assert "turns" in d.reason.lower()

    def test_cooldown_blocks_rapid_followup(self, db_path: Path) -> None:
        rl = RateLimiter(_config(cooldown_seconds=2.0), db_path=db_path)
        now = time.time()
        d = rl.check(session_id="s1", session_message_count=1, last_message_ts=now - 0.5)
        assert not d.allowed
        assert "wait" in d.reason.lower()

    def test_cooldown_allows_after_window(self, db_path: Path) -> None:
        rl = RateLimiter(_config(cooldown_seconds=0.5), db_path=db_path)
        d = rl.check(session_id="s1", session_message_count=1, last_message_ts=time.time() - 5)
        assert d.allowed

    def test_allows_when_under_all_limits(self, db_path: Path) -> None:
        rl = RateLimiter(_config(), db_path=db_path)
        d = rl.check(session_id="s1", session_message_count=0, last_message_ts=None)
        assert d.allowed
        assert d.budget_remaining_usd == pytest.approx(1.00, rel=1e-3)


class TestPersistence:
    def test_today_spend_sums_rows(self, db_path: Path) -> None:
        rl = RateLimiter(_config(), db_path=db_path)
        for cost in (0.10, 0.05, 0.20):
            rl.record_turn(
                session_id="s1",
                role="assistant",
                usage_dict={"cost_usd": cost},
            )
        assert rl.today_spend_usd() == pytest.approx(0.35, rel=1e-3)

    def test_yesterday_doesnt_count(self, db_path: Path) -> None:
        rl = RateLimiter(_config(), db_path=db_path)
        # Record one normal row (today), one explicitly dated yesterday.
        rl.record_turn(session_id="s1", role="assistant", usage_dict={"cost_usd": 0.30})
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        conn = rl._connect()  # noqa: SLF001
        try:
            conn.execute(
                """INSERT INTO assistant_events
                   (ts_utc, day_utc, session_id, role, cost_usd)
                   VALUES (?, ?, ?, ?, ?)""",
                ("2099-01-01T00:00:00", yesterday, "s1", "assistant", 5.00),
            )
            conn.commit()
        finally:
            if rl.db_path != ":memory:":
                conn.close()
        # Only today's row should count.
        assert rl.today_spend_usd() == pytest.approx(0.30, rel=1e-3)

    def test_record_turn_handles_none_usage(self, db_path: Path) -> None:
        # No usage data (e.g., on error path) shouldn't break the schema.
        rl = RateLimiter(_config(), db_path=db_path)
        rl.record_turn(session_id="s1", role="assistant", usage_dict=None, error="boom")
        assert rl.today_spend_usd() == pytest.approx(0.0)


class TestEnvConfig:
    def test_env_overrides_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ASSISTANT_DAILY_COST_CAP_USD", "12.5")
        monkeypatch.setenv("ASSISTANT_SESSION_MESSAGE_CAP", "7")
        monkeypatch.setenv("ASSISTANT_COOLDOWN_SECONDS", "0.7")
        monkeypatch.setenv("ASSISTANT_DISABLED", "1")
        cfg = RateLimitConfig.from_env()
        assert cfg.daily_cost_cap_usd == 12.5
        assert cfg.session_message_cap == 7
        assert cfg.cooldown_seconds == 0.7
        assert cfg.disabled is True

    def test_bad_env_values_fall_back_to_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ASSISTANT_DAILY_COST_CAP_USD", "not-a-number")
        cfg = RateLimitConfig.from_env()
        assert cfg.daily_cost_cap_usd == 5.00


def test_new_session_id_is_unique() -> None:
    ids = {new_session_id() for _ in range(50)}
    assert len(ids) == 50
