"""Build's free-text translation calls and the Ask daily cost cap.

Defect (2026-10 hunt): ``translate_values_text`` (Build's public "Translate to
a package" button, ``app_pages/build.py``) and ``translate_goal_text`` each
make a paid model call, but neither checked ``ASSISTANT_DAILY_COST_CAP_USD`` /
``ASSISTANT_DISABLED`` before spending nor wrote a row to the
``assistant_events`` ledger the cap sums — so a public button could spend
without limit and without trace.

Fake clients only; nothing here reaches Anthropic.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from fiscal_model.assistant.cost import _MODEL_PRICES
from fiscal_model.assistant.rate_limit import (
    EVENT_ROLE_TRANSLATE,
    EVENT_ROLE_TURN,
    RateLimitConfig,
    RateLimiter,
)
from fiscal_model.composer import translate as tr

_VALUES_PAYLOAD: dict[str, Any] = {
    "redistribution": "very_high",
    "deficit_concern": "high",
    "govt_size": "moderate",
    "growth_priority": "low",
    "generational_weight": "moderate",
    "protected": ["middle_class_rates", "ss_benefits"],
    "target_pct_gdp": 3.0,
    "reading": "You want the debt down, but not on the middle class.",
}

_GOAL_PAYLOAD: dict[str, Any] = {
    "spending_goals": [{"category": "education", "label": "Child care"}],
    "revenue_philosophy": "progressive",
    "deficit_stance": "neutral",
}


class _Client:
    def __init__(self, tool_name: str, payload: Any, usage: Any) -> None:
        self.calls: list[dict[str, Any]] = []
        self._msg = SimpleNamespace(
            content=[{"type": "tool_use", "name": tool_name, "input": payload}],
            usage=usage,
        )
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self._msg


def _usage(i: int = 1200, o: int = 150) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=i,
        output_tokens=o,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        server_tool_use=None,
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
                "SELECT session_id, role, model, input_tokens, output_tokens, cost_usd "
                "FROM assistant_events ORDER BY id"
            ).fetchall()
        ]
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv(tr.MODEL_ENV_VAR, raising=False)
    monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "default.db"))
    monkeypatch.delenv("ASSISTANT_DISABLED", raising=False)


def _values_client() -> _Client:
    return _Client(tr.VALUES_TOOL_NAME, _VALUES_PAYLOAD, _usage())


def _goal_client() -> _Client:
    return _Client(tr.TOOL_NAME, _GOAL_PAYLOAD, _usage())


def _expected_cost(model: str, i: int = 1200, o: int = 150) -> float:
    in_p, out_p = _MODEL_PRICES[model]
    return (i * in_p + o * out_p) / 1_000_000


# ---------------------------------------------------------------------------
# translate_values_text (the public Build button)
# ---------------------------------------------------------------------------


def test_values_translation_records_its_usage_in_the_cap_ledger(tmp_path) -> None:
    limiter = _limiter(tmp_path)
    client = _values_client()
    vector, _reading, reason = tr.translate_values_text(
        "progressive", client=client, limiter=limiter, session_id="build-1"
    )
    assert vector is not None and reason == ""
    rows = _rows(limiter)
    assert len(rows) == 1
    row = rows[0]
    assert row["role"] == EVENT_ROLE_TRANSLATE != EVENT_ROLE_TURN
    assert row["model"] == tr.DEFAULT_MODEL
    assert row["session_id"] == "build-1"
    assert (row["input_tokens"], row["output_tokens"]) == (1200, 150)
    expected = _expected_cost(tr.DEFAULT_MODEL)
    assert row["cost_usd"] == pytest.approx(expected, rel=1e-3)
    assert limiter.today_spend_usd() == pytest.approx(expected, rel=1e-3)


def test_values_translation_is_refused_over_cap_without_a_call(tmp_path) -> None:
    limiter = _limiter(tmp_path, cap=0.01)
    limiter.record_turn(session_id="s", role=EVENT_ROLE_TURN, usage_dict={"cost_usd": 0.02})
    client = _values_client()
    vector, reading, reason = tr.translate_values_text(
        "progressive", client=client, limiter=limiter
    )
    assert (vector, reading) == (None, "")
    assert "budget" in reason
    assert client.calls == []
    assert len(_rows(limiter)) == 1


def test_values_translation_is_refused_when_disabled(tmp_path) -> None:
    client = _values_client()
    vector, _, reason = tr.translate_values_text(
        "progressive", client=client, limiter=_limiter(tmp_path, disabled=True)
    )
    assert vector is None and reason
    assert client.calls == []


def test_values_translation_without_a_limiter_uses_the_shared_ledger(tmp_path) -> None:
    """The Build page passes no limiter; the spend must still count."""
    vector, _, _ = tr.translate_values_text("progressive", client=_values_client())
    assert vector is not None
    rows = _rows(RateLimiter(db_path=tmp_path / "default.db"))
    assert [r["role"] for r in rows] == [EVENT_ROLE_TRANSLATE]


def test_values_output_is_unchanged_by_the_ledger(tmp_path) -> None:
    """Same request, same parsing, same vector — the gate only adds a row."""
    client = _values_client()
    out = tr.translate_values_text("progressive", client=client, limiter=_limiter(tmp_path))
    (call,) = client.calls
    assert call["temperature"] == tr.TEMPERATURE == 0.0
    assert set(call) == {
        "model", "max_tokens", "temperature", "system", "tools", "tool_choice", "messages",
    }
    assert out[1] == _VALUES_PAYLOAD["reading"]


# ---------------------------------------------------------------------------
# translate_goal_text
# ---------------------------------------------------------------------------


def test_goal_translation_records_its_usage_in_the_cap_ledger(tmp_path) -> None:
    limiter = _limiter(tmp_path)
    spec, reason = tr.translate_goal_text("progressive", client=_goal_client(), limiter=limiter)
    assert spec is not None, reason
    rows = _rows(limiter)
    assert [r["role"] for r in rows] == [EVENT_ROLE_TRANSLATE]
    assert rows[0]["cost_usd"] == pytest.approx(_expected_cost(tr.DEFAULT_MODEL), rel=1e-3)


def test_goal_translation_is_refused_over_cap_without_a_call(tmp_path) -> None:
    client = _goal_client()
    spec, reason = tr.translate_goal_text(
        "progressive", client=client, limiter=_limiter(tmp_path, cap=0.0)
    )
    assert spec is None and "budget" in reason
    assert client.calls == []


def test_a_paid_call_with_an_unusable_reply_is_still_recorded(tmp_path) -> None:
    limiter = _limiter(tmp_path)
    client = _Client("wrong_tool", {}, _usage())
    spec, reason = tr.translate_goal_text("progressive", client=client, limiter=limiter)
    assert spec is None and reason
    assert len(_rows(limiter)) == 1


def test_the_default_model_alias_is_priced_as_haiku() -> None:
    """``claude-haiku-4-5`` must not fall through to the Opus fallback price."""
    from fiscal_model.assistant.cost import _prices_for

    assert _prices_for(tr.DEFAULT_MODEL) == _MODEL_PRICES["claude-haiku-4-5-20251001"]
