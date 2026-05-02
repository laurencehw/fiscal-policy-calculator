"""
Tests for scripts/check_public_app.py.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_public_app.py"


@pytest.fixture
def public_app_check():
    spec = importlib.util.spec_from_file_location("_public_app_check_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _response(text: str, *, status_error: Exception | None = None):
    def raise_for_status():
        if status_error is not None:
            raise status_error

    return SimpleNamespace(text=text, raise_for_status=raise_for_status)


def test_check_page_accepts_reachable_streamlit_shell(public_app_check, monkeypatch):
    seen = {}

    def fake_get(url, *, timeout, headers):
        seen["url"] = url
        seen["timeout"] = timeout
        seen["headers"] = headers
        return _response("<html><script src='streamlit.js'></script></html>")

    monkeypatch.setattr(public_app_check.requests, "get", fake_get)

    ok, message = public_app_check._check_page(
        "https://example.streamlit.app",
        timeout_seconds=7.5,
    )

    assert ok is True
    assert "looks reachable" in message
    assert seen["timeout"] == 7.5
    assert seen["headers"]["User-Agent"] == public_app_check.USER_AGENT


def test_check_page_report_includes_latency(public_app_check, monkeypatch):
    monkeypatch.setattr(
        public_app_check.requests,
        "get",
        lambda *args, **kwargs: _response("<html>ok</html>"),
    )

    report = public_app_check._check_page_report(
        "https://example.streamlit.app",
        timeout_seconds=10,
    )

    assert report["ok"] is True
    assert report["url"] == "https://example.streamlit.app"
    assert isinstance(report["latency_ms"], float)
    assert "looks reachable" in report["message"]


def test_check_page_rejects_streamlit_not_found(public_app_check, monkeypatch):
    monkeypatch.setattr(
        public_app_check.requests,
        "get",
        lambda *args, **kwargs: _response("You do not have access to this app or it does not exist"),
    )

    ok, message = public_app_check._check_page(
        "https://example.streamlit.app",
        timeout_seconds=10,
    )

    assert ok is False
    assert "not-found/access" in message


def test_check_page_rejects_empty_body(public_app_check, monkeypatch):
    monkeypatch.setattr(
        public_app_check.requests,
        "get",
        lambda *args, **kwargs: _response("   "),
    )

    ok, message = public_app_check._check_page(
        "https://example.streamlit.app",
        timeout_seconds=10,
    )

    assert ok is False
    assert "empty response" in message


def test_check_page_reports_request_exception(public_app_check, monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.Timeout("slow")

    monkeypatch.setattr(public_app_check.requests, "get", fake_get)

    ok, message = public_app_check._check_page(
        "https://example.streamlit.app",
        timeout_seconds=10,
    )

    assert ok is False
    assert "failed" in message


def test_issues_from_reports_returns_failed_urls(public_app_check):
    reports = [
        {
            "url": "https://example.test",
            "ok": True,
            "latency_ms": 12.3,
            "message": "ok",
        },
        {
            "url": "https://example.test/?mode=classroom",
            "ok": False,
            "latency_ms": 45.6,
            "message": "not found",
        },
    ]

    issues = public_app_check._issues_from_reports(reports)

    assert len(issues) == 1
    assert issues[0]["surface"] == "public_app"
    assert issues[0]["severity"] == "fail"
    assert issues[0]["url"] == "https://example.test/?mode=classroom"
    assert issues[0]["latency_ms"] == 45.6


def test_json_mode_emits_machine_readable_report(public_app_check, monkeypatch, capsys):
    def fake_report(url: str, timeout_seconds: float):
        return {
            "url": url,
            "ok": True,
            "latency_ms": timeout_seconds,
            "message": f"{url} ok",
        }

    monkeypatch.setattr(public_app_check, "_check_page_report", fake_report)
    monkeypatch.setattr(sys, "argv", ["check_public_app", "--url", "https://example.test", "--json"])

    assert public_app_check.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["overall"] == "ok"
    assert payload["issues"] == []
    assert len(payload["checks"]) == 2
    assert payload["checks"][1]["url"] == "https://example.test/?mode=classroom"


def test_json_mode_reports_failed_issues(public_app_check, monkeypatch, capsys):
    def fake_report(url: str, timeout_seconds: float):
        del timeout_seconds
        ok = not url.endswith("mode=classroom")
        return {
            "url": url,
            "ok": ok,
            "latency_ms": 1.0,
            "message": "ok" if ok else "classroom failed",
        }

    monkeypatch.setattr(public_app_check, "_check_page_report", fake_report)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_public_app", "--url", "https://example.test", "--json"],
    )

    assert public_app_check.main() == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["overall"] == "failed"
    assert len(payload["issues"]) == 1
    assert payload["issues"][0]["message"] == "classroom failed"


def test_human_mode_prints_issues_on_failure(public_app_check, monkeypatch, capsys):
    def fake_report(url: str, timeout_seconds: float):
        del timeout_seconds
        return {
            "url": url,
            "ok": False,
            "latency_ms": 1.0,
            "message": f"{url} failed",
        }

    monkeypatch.setattr(public_app_check, "_check_page_report", fake_report)
    monkeypatch.setattr(sys, "argv", ["check_public_app", "--url", "https://example.test"])

    assert public_app_check.main() == 1
    out = capsys.readouterr().out
    assert "Issues:" in out
    assert "Public app checks failed." in out
