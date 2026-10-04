"""Auxiliary paid calls (follow-up chips, prompt-cache pre-warm) and the cap.

Defect (2026-10 hunt): ``FiscalAssistant.suggest_followups`` (a Haiku call
after every answer) and ``FiscalAssistant.prewarm_cache`` (a Sonnet call that
writes the ~3 KB system block to the prompt cache at app boot) both spent
real money, but neither wrote a row to the ``assistant_events`` ledger that
:meth:`RateLimiter.today_spend_usd` sums — so that spend never counted
against ``ASSISTANT_DAILY_COST_CAP_USD``, and both kept spending after the
cap (or the ``ASSISTANT_DISABLED`` kill switch) had closed the main path.

These tests use a fake client only; nothing here reaches Anthropic.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from fiscal_model.assistant import FiscalAssistant
from fiscal_model.assistant import admin as admin_queries
from fiscal_model.assistant.cost import _MODEL_PRICES
from fiscal_model.assistant.rate_limit import (
    EVENT_ROLE_FOLLOWUPS,
    EVENT_ROLE_PREWARM,
    EVENT_ROLE_TURN,
    RateLimitConfig,
    RateLimiter,
)

HAIKU = "claude-haiku-4-5-20251001"


class _Messages:
    def __init__(self, text: str, usage: Any) -> None:
        self.calls: list[dict[str, Any]] = []
        self._text = text
        self._usage = usage

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(text=self._text)],
            usage=self._usage,
            stop_reason="end_turn",
        )


class _Client:
    def __init__(self, text: str = "", usage: Any = None) -> None:
        self.messages = _Messages(text, usage)


def _usage(i: int, o: int, cw: int = 0, cr: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=i,
        output_tokens=o,
        cache_creation_input_tokens=cw,
        cache_read_input_tokens=cr,
        server_tool_use=None,
    )


def _assistant(client: _Client) -> FiscalAssistant:
    return FiscalAssistant(
        scorer=None,
        baseline=None,
        cbo_score_map={},
        presets={},
        anthropic_client=client,
    )


def _limiter(tmp_path, cap: float = 5.0, disabled: bool = False) -> RateLimiter:
    return RateLimiter(
        config=RateLimitConfig(daily_cost_cap_usd=cap, disabled=disabled),
        db_path=tmp_path / "usage.db",
    )


def _rows(limiter: RateLimiter) -> list[dict[str, Any]]:
    conn = limiter._connect()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT session_id, role, model, input_tokens, output_tokens, "
                "cache_creation_tokens, cost_usd FROM assistant_events ORDER BY id"
            ).fetchall()
        ]
    finally:
        conn.close()


FOLLOWUP_TEXT = "Why?\nHow does it compare?\nWho pays?"


# ---------------------------------------------------------------------------
# Follow-ups
# ---------------------------------------------------------------------------


def test_followups_record_their_usage_in_the_cap_ledger(tmp_path) -> None:
    client = _Client(FOLLOWUP_TEXT, _usage(1000, 100))
    limiter = _limiter(tmp_path)
    out = _assistant(client).suggest_followups(
        "q", "a", limiter=limiter, session_id="sess-1"
    )
    assert out == ["Why?", "How does it compare?", "Who pays?"]

    rows = _rows(limiter)
    assert len(rows) == 1
    row = rows[0]
    in_p, out_p = _MODEL_PRICES[HAIKU]
    expected = (1000 * in_p + 100 * out_p) / 1_000_000
    assert row["role"] == EVENT_ROLE_FOLLOWUPS != EVENT_ROLE_TURN
    assert row["model"] == HAIKU
    assert row["session_id"] == "sess-1"
    assert (row["input_tokens"], row["output_tokens"]) == (1000, 100)
    assert row["cost_usd"] == pytest.approx(expected, rel=1e-3)
    # The spend is what the daily cap reads.
    assert limiter.today_spend_usd() == pytest.approx(expected, rel=1e-3)


def test_followups_skip_the_call_when_over_cap(tmp_path) -> None:
    client = _Client(FOLLOWUP_TEXT, _usage(1000, 100))
    limiter = _limiter(tmp_path, cap=0.01)
    limiter.record_turn(
        session_id="s", role=EVENT_ROLE_TURN, usage_dict={"cost_usd": 0.02}
    )
    out = _assistant(client).suggest_followups("q", "a", limiter=limiter)
    assert out == []
    assert client.messages.calls == []
    assert len(_rows(limiter)) == 1  # nothing new


def test_followups_skip_the_call_when_disabled(tmp_path) -> None:
    client = _Client(FOLLOWUP_TEXT, _usage(1000, 100))
    limiter = _limiter(tmp_path, disabled=True)
    assert _assistant(client).suggest_followups("q", "a", limiter=limiter) == []
    assert client.messages.calls == []


def test_followups_record_even_when_the_reply_is_unusable(tmp_path) -> None:
    """A paid call whose text yields no questions is still paid for."""
    client = _Client("", _usage(500, 3))
    limiter = _limiter(tmp_path)
    assert _assistant(client).suggest_followups("q", "a", limiter=limiter) == []
    assert len(_rows(limiter)) == 1
    assert limiter.today_spend_usd() > 0


def test_followups_without_an_explicit_limiter_still_use_the_ledger(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No caller can opt out of the ledger by omitting it."""
    db = tmp_path / "default.db"
    monkeypatch.setenv("ASSISTANT_USAGE_DB", str(db))
    client = _Client(FOLLOWUP_TEXT, _usage(1000, 100))
    _assistant(client).suggest_followups("q", "a")
    assert len(_rows(RateLimiter(db_path=db))) == 1


# ---------------------------------------------------------------------------
# Pre-warm
# ---------------------------------------------------------------------------


def test_prewarm_records_its_usage_in_the_cap_ledger(tmp_path) -> None:
    client = _Client("ok", _usage(5, 2, cw=3000))
    limiter = _limiter(tmp_path)
    assistant = _assistant(client)
    assert assistant.prewarm_cache(limiter=limiter) is True

    rows = _rows(limiter)
    assert len(rows) == 1
    row = rows[0]
    in_p, out_p = _MODEL_PRICES[assistant._model]
    expected = (5 * in_p + 2 * out_p + 3000 * in_p * 1.25) / 1_000_000
    assert row["role"] == EVENT_ROLE_PREWARM
    assert row["model"] == assistant._model
    assert row["cache_creation_tokens"] == 3000
    assert row["cost_usd"] == pytest.approx(expected, rel=1e-3)
    assert limiter.today_spend_usd() == pytest.approx(expected, rel=1e-3)
    # Idempotent: the second call spends nothing and writes nothing.
    assert assistant.prewarm_cache(limiter=limiter) is False
    assert len(client.messages.calls) == 1
    assert len(_rows(limiter)) == 1


def test_prewarm_skips_the_call_when_over_cap(tmp_path) -> None:
    client = _Client("ok", _usage(5, 2, cw=3000))
    limiter = _limiter(tmp_path, cap=0.0)
    assert _assistant(client).prewarm_cache(limiter=limiter) is False
    assert client.messages.calls == []
    assert _rows(limiter) == []


def test_prewarm_skips_the_call_when_disabled(tmp_path) -> None:
    client = _Client("ok", _usage(5, 2, cw=3000))
    limiter = _limiter(tmp_path, disabled=True)
    assert _assistant(client).prewarm_cache(limiter=limiter) is False
    assert client.messages.calls == []


def test_budget_check_ignores_session_caps(tmp_path) -> None:
    """The auxiliary gate is the money gate only, not the per-user turn caps."""
    limiter = _limiter(tmp_path)
    decision = limiter.check_budget()
    assert decision.allowed
    assert decision.daily_cap_usd == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Admin queries tell the kinds apart and keep "turns" meaning turns
# ---------------------------------------------------------------------------


def test_admin_counts_turns_but_sums_all_spend(tmp_path) -> None:
    limiter = _limiter(tmp_path)
    limiter.record_turn(session_id="a", role=EVENT_ROLE_TURN, usage_dict={"cost_usd": 0.03})
    limiter.record_turn(
        session_id="a", role=EVENT_ROLE_FOLLOWUPS, model=HAIKU, usage_dict={"cost_usd": 0.001}
    )
    limiter.record_turn(
        session_id="boot", role=EVENT_ROLE_PREWARM, usage_dict={"cost_usd": 0.012}
    )

    snap = admin_queries.snapshot(limiter)
    assert snap.total_turns == 1
    assert snap.today_turns == 1
    assert snap.total_cost_usd == pytest.approx(0.043)
    assert snap.today_cost_usd == pytest.approx(0.043)
    assert snap.n_unique_sessions_30d == 1

    daily = admin_queries.daily_spend_series(limiter, days=2)
    assert daily.iloc[-1]["cost_usd"] == pytest.approx(0.043)
    assert daily.iloc[-1]["turns"] == 1

    by_kind = admin_queries.spend_by_kind(limiter, days=30)
    assert isinstance(by_kind, pd.DataFrame)
    got = dict(zip(by_kind["kind"], by_kind["cost_usd"], strict=True))
    assert got == pytest.approx(
        {EVENT_ROLE_TURN: 0.03, EVENT_ROLE_PREWARM: 0.012, EVENT_ROLE_FOLLOWUPS: 0.001}
    )

    recent = admin_queries.recent_turns(limiter, limit=10)
    assert list(recent["kind"]) == [EVENT_ROLE_PREWARM, EVENT_ROLE_FOLLOWUPS, EVENT_ROLE_TURN]


def test_prewarm_without_an_explicit_limiter_still_uses_the_ledger(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The boot-time pre-warm (``ui/dependencies.py``) passes no limiter."""
    db = tmp_path / "default.db"
    monkeypatch.setenv("ASSISTANT_USAGE_DB", str(db))
    client = _Client("ok", _usage(5, 2, cw=3000))
    assert _assistant(client).prewarm_cache() is True
    rows = _rows(RateLimiter(db_path=db))
    assert [r["role"] for r in rows] == [EVENT_ROLE_PREWARM]


def test_ask_page_passes_its_ledger_and_session_to_followups(tmp_path) -> None:
    from fiscal_model.ui.tabs import ask_assistant as page

    limiter = _limiter(tmp_path)
    seen: dict[str, Any] = {}

    class _Fake:
        def suggest_followups(self, **kwargs: Any) -> list[str]:
            seen.update(kwargs)
            return []

    state = {page._LIMITER_CACHE_KEY: limiter, page._SESSION_ID_KEY: "sess-9"}
    turn = {"followups_seed": {"question": "q", "answer": "a"}}
    page._maybe_generate_and_render_followups(None, state, _Fake(), turn)
    assert seen["limiter"] is limiter
    assert seen["session_id"] == "sess-9"
