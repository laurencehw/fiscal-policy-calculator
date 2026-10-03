"""``/ask`` and ``/ask/stream``: upstream failures, per-request assistants.

Reproduced before the fix: an Anthropic failure was spliced into the answer
text and returned as HTTP 200, with a ledger row recording no error; and
``enable_web_search`` was written onto the shared singleton, so concurrent
requests overwrote each other's toggle (and per-turn state).

Mocks the Anthropic client; no API credit is spent.
"""

from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

import api as api_module
from fiscal_model.assistant import AssistantUpstreamError, FiscalAssistant


class _UpstreamDown(Exception):
    status_code = 529


class _FailingMessages:
    def stream(self, **kwargs: Any):
        raise _UpstreamDown("overloaded_error: SECRET-UPSTREAM-DETAIL")


class _FailingClient:
    messages = _FailingMessages()


class _OkStream:
    def __enter__(self) -> _OkStream:
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    @property
    def text_stream(self):
        return iter(["Fine."])

    def get_final_message(self) -> Any:
        usage = SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Fine.")],
            stop_reason="end_turn",
            usage=usage,
        )


class _OkClient:
    class messages:
        @staticmethod
        def stream(**kwargs: Any) -> _OkStream:
            return _OkStream()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path):
    api_module._ASK_ASSISTANT = None
    api_module._ASK_LIMITER = None
    monkeypatch.delenv("FPC_API_KEYS", raising=False)
    monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "usage.db"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    yield tmp_path / "usage.db"
    api_module._ASK_ASSISTANT = None
    api_module._ASK_LIMITER = None


def _client_with(monkeypatch: pytest.MonkeyPatch, anthropic_client: Any) -> TestClient:
    real_build = api_module._build_api_assistant

    def _build():
        assistant = real_build()
        assistant._client = anthropic_client
        return assistant

    monkeypatch.setattr(api_module, "_build_api_assistant", _build)
    return TestClient(api_module.app)


def _ledger(db_path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return list(conn.execute("SELECT * FROM assistant_events ORDER BY id"))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# upstream failure -> 502 / SSE error, with the ledger row recorded
# ---------------------------------------------------------------------------


def test_ask_upstream_failure_is_a_502_with_an_error_ledger_row(
    monkeypatch, _isolate
):
    client = _client_with(monkeypatch, _FailingClient())
    response = client.post(
        "/ask", json={"question": "What is the deficit?", "session_id": "s-502"}
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "529" in detail
    assert "SECRET-UPSTREAM-DETAIL" not in response.text  # no raw SDK text

    rows = _ledger(_isolate)
    assert len(rows) == 1
    assert rows[0]["session_id"] == "s-502"
    assert rows[0]["error"] and "AssistantUpstreamError" in rows[0]["error"]


def test_ask_stream_upstream_failure_emits_an_sse_error_event(monkeypatch, _isolate):
    client = _client_with(monkeypatch, _FailingClient())
    response = client.post(
        "/ask/stream", json={"question": "What is the deficit?", "session_id": "s-sse"}
    )
    assert response.status_code == 200  # the stream was already open
    body = response.text
    assert "event: error" in body
    assert "event: done" not in body
    assert "SECRET-UPSTREAM-DETAIL" not in body
    frame = body.split("event: error\ndata: ", 1)[1].split("\n", 1)[0]
    payload = json.loads(frame)
    assert payload["status"] == 502
    assert payload["upstream_status"] == 529

    rows = _ledger(_isolate)
    assert len(rows) == 1 and rows[0]["error"]


def test_a_code_bug_is_a_500_not_a_502(monkeypatch, _isolate):
    client = _client_with(monkeypatch, _OkClient())

    def _boom(self, *args, **kwargs):
        raise KeyError("internal bug detail")
        yield  # pragma: no cover

    monkeypatch.setattr(FiscalAssistant, "stream_response", _boom)
    response = client.post("/ask", json={"question": "hi", "session_id": "s-500"})
    assert response.status_code == 500
    assert "internal bug detail" not in response.text
    assert _ledger(_isolate)[0]["error"]


def test_a_successful_turn_still_records_no_error(monkeypatch, _isolate):
    client = _client_with(monkeypatch, _OkClient())
    response = client.post("/ask", json={"question": "hi", "session_id": "s-ok"})
    assert response.status_code == 200
    assert response.json()["answer"] == "Fine."
    rows = _ledger(_isolate)
    assert len(rows) == 1 and rows[0]["error"] is None
    assert rows[0]["input_tokens"] == 10


# ---------------------------------------------------------------------------
# per-request assistants
# ---------------------------------------------------------------------------


def test_the_web_search_toggle_never_lands_on_the_shared_assistant(monkeypatch):
    client = _client_with(monkeypatch, _OkClient())
    shared = api_module._get_ask_assistant()
    before = shared._enable_web_search
    seen: list[bool] = []
    real_spawn = FiscalAssistant.spawn

    def _spy(self, **kwargs):
        clone = real_spawn(self, **kwargs)
        seen.append(clone._enable_web_search)
        assert clone is not self
        return clone

    monkeypatch.setattr(FiscalAssistant, "spawn", _spy)
    for flag in (False, True, False):
        response = client.post(
            "/ask", json={"question": "hi", "enable_web_search": flag}
        )
        assert response.status_code == 200
    assert seen == [False, True, False]
    assert shared._enable_web_search == before
    # Per-turn state stayed on the copies.
    assert shared.last_full_text == ""
    assert shared.last_usage is None


def test_spawn_helper_falls_back_to_the_singleton_without_touching_it():
    class _Legacy:
        _enable_web_search = True

    legacy = _Legacy()
    got = api_module._spawn_request_assistant(legacy, enable_web_search=False)
    assert got is legacy
    assert legacy._enable_web_search is True  # the shared toggle is not written


def test_spawn_helper_prefers_spawn_then_clone_for_request():
    class _Cloning:
        _enable_web_search = True

        def clone_for_request(self):
            clone = _Cloning()
            return clone

    base = _Cloning()
    got = api_module._spawn_request_assistant(base, enable_web_search=False)
    assert got is not base
    assert got._enable_web_search is False
    assert base._enable_web_search is True


def test_upstream_error_type_is_the_assistant_packages():
    assert api_module.AssistantUpstreamError is AssistantUpstreamError
