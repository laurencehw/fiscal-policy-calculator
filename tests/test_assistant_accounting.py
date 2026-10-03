"""Usage accounting, upstream errors and per-request state for ``FiscalAssistant``.

Defects (2026-10 hunt):

* usage was booked *after* the answer was yielded and recorded by code after
  the caller's ``for`` loop, so a client that disconnected mid-stream left a
  completed, paid call off the ledger;
* an Anthropic failure was spliced into the answer text and returned as a
  normal 200, recorded as an error-free turn;
* ``cost.py`` ignored web-search charges and priced unknown models as Sonnet;
* one ``FiscalAssistant`` served every request, so ``last_usage`` /
  provenance / scoring context crossed between concurrent requests.
"""

from __future__ import annotations

import logging
import threading
from types import SimpleNamespace
from typing import Any

import pytest

from fiscal_model.assistant import AssistantUpstreamError, FiscalAssistant
from fiscal_model.assistant.cost import (
    _MODEL_PRICES,
    WEB_SEARCH_USD_PER_1000,
    ConversationCost,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _usage(i: int = 0, o: int = 0, searches: int | None = None) -> SimpleNamespace:
    server = SimpleNamespace(web_search_requests=searches) if searches is not None else None
    return SimpleNamespace(
        input_tokens=i,
        output_tokens=o,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        server_tool_use=server,
    )


class _Msg:
    def __init__(self, usage: Any, content: list[Any] | None = None, stop: str = "end_turn"):
        self.usage = usage
        self.content = content or []
        self.stop_reason = stop


class _Stream:
    def __init__(self, text: str, msg: _Msg, fail: Exception | None = None):
        self._text, self._msg, self._fail = text, msg, fail

    def __enter__(self) -> _Stream:
        return self

    def __exit__(self, *a: Any) -> bool:
        return False

    @property
    def text_stream(self):
        if self._fail is not None:
            raise self._fail
        yield from (self._text[:5], self._text[5:])

    def get_final_message(self) -> _Msg:
        return self._msg


class _Client:
    """``messages.stream`` returns whatever ``script`` yields next."""

    def __init__(self, script):
        self._script = iter(script)
        self.messages = SimpleNamespace(stream=self._stream)

    def _stream(self, **kw: Any) -> _Stream:
        item = next(self._script)
        return item(kw) if callable(item) else item


def _assistant(client: Any, **kw: Any) -> FiscalAssistant:
    return FiscalAssistant(
        scorer=None,
        baseline=None,
        cbo_score_map={},
        presets={},
        anthropic_client=client,
        enable_web_search=False,
        **kw,
    )


# ---------------------------------------------------------------------------
# (a) usage survives a client disconnect
# ---------------------------------------------------------------------------


def test_usage_is_recorded_when_the_client_disconnects_mid_stream() -> None:
    client = _Client([_Stream("Hello world", _Msg(_usage(1_000, 200)))])
    a = _assistant(client)
    seen: list[dict[str, Any]] = []
    gen = a.stream_response("q", [], on_turn_end=seen.append)
    assert next(gen) == "Hello"  # the paid call has already completed
    gen.close()  # client went away: GeneratorExit at the yield

    assert len(seen) == 1, "turn-end callback must fire exactly once"
    info = seen[0]
    assert info["disconnected"] is True
    assert info["error"] is None
    assert info["usage"]["input_tokens"] == 1_000
    assert info["usage"]["output_tokens"] == 200
    assert info["usage"]["cost_usd"] > 0
    assert a.last_usage is not None and a.last_usage.input_tokens == 1_000


def test_callback_fires_once_on_normal_completion_and_constructor_callback_works() -> None:
    seen: list[dict[str, Any]] = []
    a = _assistant(_Client([_Stream("Hello world", _Msg(_usage(10, 5)))]), on_turn_end=seen.append)
    text = "".join(a.stream_response("q", []))
    assert text.startswith("Hello world")
    assert len(seen) == 1 and seen[0]["disconnected"] is False and seen[0]["error"] is None
    assert seen[0]["answer_chars"] > 0
    assert a.last_error is None


# ---------------------------------------------------------------------------
# (b) upstream failure is an error, not answer text
# ---------------------------------------------------------------------------


def test_upstream_failure_raises_typed_error_and_is_recorded_with_error() -> None:
    boom = RuntimeError("overloaded_error")
    a = _assistant(_Client([_Stream("", _Msg(None), fail=boom)]))
    seen: list[dict[str, Any]] = []
    chunks: list[str] = []
    with pytest.raises(AssistantUpstreamError) as ei:
        for c in a.stream_response("q", [], on_turn_end=seen.append):
            chunks.append(c)
    assert chunks == []  # nothing appended to the answer
    assert "overloaded_error" in str(ei.value)
    assert ei.value.__cause__ is boom
    assert a.last_error and "AssistantUpstreamError" in a.last_error
    assert "Error from Anthropic" not in a.last_full_text
    assert len(seen) == 1 and seen[0]["error"] and "overloaded_error" in seen[0]["error"]


def test_failure_after_a_completed_call_still_records_that_calls_usage() -> None:
    tool_msg = _Msg(
        _usage(5_000, 100),
        content=[SimpleNamespace(type="tool_use", id="t1", name="list_presets", input={})],
        stop="tool_use",
    )
    a = _assistant(
        _Client([_Stream("", tool_msg), _Stream("", _Msg(None), fail=RuntimeError("503"))])
    )
    seen: list[dict[str, Any]] = []
    with pytest.raises(AssistantUpstreamError):
        list(a.stream_response("q", [], on_turn_end=seen.append))
    assert seen[0]["error"]
    assert seen[0]["usage"]["input_tokens"] == 5_000
    assert seen[0]["tools_used"] == ["list_presets"]


def test_error_exported_from_package_root() -> None:
    import fiscal_model.assistant as pkg

    assert pkg.AssistantUpstreamError is AssistantUpstreamError
    assert issubclass(AssistantUpstreamError, RuntimeError)


# ---------------------------------------------------------------------------
# (c) cost pricing
# ---------------------------------------------------------------------------


def test_web_search_requests_are_priced() -> None:
    cc = ConversationCost()
    base = cc.record(_usage(1_000, 100), "claude-sonnet-4-6").cost_usd
    with_search = cc.record(_usage(1_000, 100, searches=7), "claude-sonnet-4-6")
    assert with_search.web_search_requests == 7
    assert with_search.cost_usd - base == pytest.approx(7 * WEB_SEARCH_USD_PER_1000 / 1000)
    assert WEB_SEARCH_USD_PER_1000 == 10.0
    assert with_search.to_dict()["web_search_requests"] == 7


def test_web_search_requests_read_from_a_dict_usage_and_ignore_junk() -> None:
    cc = ConversationCost()
    t = cc.record(
        {"input_tokens": 0, "output_tokens": 0, "server_tool_use": {"web_search_requests": 3}},
        "claude-sonnet-4-6",
    )
    assert t.cost_usd == pytest.approx(0.03)
    junk = cc.record(SimpleNamespace(input_tokens=0, server_tool_use=object()), "claude-sonnet-4-6")
    assert junk.web_search_requests == 0


def test_unknown_model_is_not_priced_as_sonnet_and_warns(caplog: pytest.LogCaptureFixture) -> None:
    usage = _usage(1_000_000, 1_000_000)
    sonnet = ConversationCost().record(usage, "claude-sonnet-4-6").cost_usd
    top_in, top_out = max(_MODEL_PRICES.values(), key=lambda p: (p[1], p[0]))
    with caplog.at_level(logging.WARNING, logger="fiscal_model.assistant.cost"):
        unknown = ConversationCost().record(usage, "claude-future-9-9").cost_usd
        ConversationCost().record(usage, "claude-future-9-9")
    assert unknown == pytest.approx(top_in + top_out)
    assert unknown > sonnet
    warned = [r for r in caplog.records if "claude-future-9-9" in r.getMessage()]
    assert len(warned) == 1, "one warning per unknown id, not one per call"


def test_dated_snapshot_of_a_known_model_prices_as_that_model(
    caplog: pytest.LogCaptureFixture,
) -> None:
    usage = _usage(1_000_000, 0)
    with caplog.at_level(logging.WARNING, logger="fiscal_model.assistant.cost"):
        cost = ConversationCost().record(usage, "claude-sonnet-4-6-20260301").cost_usd
    assert cost == pytest.approx(3.0)
    assert not caplog.records


def test_turn_usage_aggregates_web_searches_across_iterations() -> None:
    a = _assistant(_Client([]))
    a._record_usage(_usage(10, 1, searches=2))
    a._record_usage(_usage(10, 1, searches=3))
    assert a.last_usage is not None and a.last_usage.web_search_requests == 5


# ---------------------------------------------------------------------------
# (5) per-request state
# ---------------------------------------------------------------------------


def test_concurrent_spawned_assistants_do_not_cross_usage_or_provenance() -> None:
    alice_started = threading.Event()
    bob_done = threading.Event()

    def alice_stream(kw: dict[str, Any]) -> _Stream:
        alice_started.set()
        assert bob_done.wait(5)  # Alice's call is the slow one
        return _Stream("ALICE-ANSWER", _Msg(_usage(1_000_000, 10)))

    def bob_stream(kw: dict[str, Any]) -> _Stream:
        return _Stream("BOB-ANSWER", _Msg(_usage(10, 10)))

    class _Router:
        def __init__(self) -> None:
            self.messages = SimpleNamespace(stream=self._stream)

        def _stream(self, **kw: Any) -> _Stream:
            q = kw["messages"][-1]["content"]
            return alice_stream(kw) if "ALICE" in q else bob_stream(kw)

    shared = _assistant(_Router())
    results: dict[str, Any] = {}

    def run(name: str, q: str, ctx: dict[str, Any]) -> None:
        a = shared.spawn()
        text = "".join(a.stream_response(q, [], scoring_context=ctx))
        results[name] = (text, a)
        if name == "bob":
            bob_done.set()

    ta = threading.Thread(target=run, args=("alice", "ALICE asks", {"policy_name": "alice-private"}))
    tb = threading.Thread(target=run, args=("bob", "BOB asks", {"policy_name": "bob-private"}))
    ta.start()
    assert alice_started.wait(5)
    tb.start()
    ta.join(10)
    tb.join(10)

    a_text, a_asst = results["alice"]
    b_text, b_asst = results["bob"]
    assert a_text.startswith("ALICE-ANSWER") and b_text.startswith("BOB-ANSWER")
    assert a_asst.last_usage.input_tokens == 1_000_000
    assert b_asst.last_usage.input_tokens == 10
    assert a_asst._tools._scoring_context == {"policy_name": "alice-private"}
    assert b_asst._tools._scoring_context == {"policy_name": "bob-private"}
    # the template instance was never used as a turn carrier
    assert shared.last_usage is None and shared._tools._scoring_context is None


def test_spawn_shares_immutables_and_isolates_turn_state() -> None:
    parent = _assistant(_Client([]))
    child = parent.spawn(enable_web_search=True)
    assert child is not parent
    assert child.client is parent.client
    assert child._tools is not parent._tools
    assert child._tools._scorer is parent._tools._scorer
    assert child._tools._knowledge_searcher is parent._tools._knowledge_searcher
    assert child.cost is not parent.cost
    assert child._enable_web_search is True and parent._enable_web_search is False
    child._tools.provenance.append({"tool": "x"})
    child._tools.set_scoring_context({"a": 1})
    assert parent._tools.provenance == [] and parent._tools._scoring_context is None
