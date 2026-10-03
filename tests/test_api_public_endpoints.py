"""Unauthenticated /health, /summary, /readiness: no host details, cheap repeats.

Reproduced before the fix: all three returned the absolute path of the repo's
microdata file and usage database, ``sys.executable`` and
``api_key_configured``, and ``/readiness`` re-ran the whole release gate
(~2-8s) on every call.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api as api_module
from fiscal_model.readiness import ReadinessCheck, ReadinessReport

REPO_ROOT = str(Path(api_module.__file__).resolve().parent)


def _client() -> TestClient:
    return TestClient(api_module.app)


def _assert_no_host_details(text: str) -> None:
    assert REPO_ROOT not in text
    assert sys.executable not in text
    for key in ("api_key_configured", '"executable"', "usage_db_path"):
        assert key not in text, key
    for prefix in ("/home/", "/usr/", "/root/", "/tmp/", "/Users/"):
        assert prefix not in text, prefix


@pytest.mark.parametrize("path", ["/health", "/summary"])
def test_public_endpoints_leak_no_host_details(path):
    response = _client().get(path)
    assert response.status_code == 200
    _assert_no_host_details(response.text)


def test_health_keeps_the_fields_clients_read():
    payload = _client().get("/health").json()
    assert {"overall", "timestamp", "components", "issues"} <= set(payload)
    components = payload["components"]
    assert {"runtime", "baseline", "microdata", "assistant"} <= set(components)
    assert components["runtime"]["python_version"]
    assert "executable" not in components["runtime"]
    # A path is reduced to something relative, not dropped.
    path = components["microdata"]["path"]
    assert not Path(path).is_absolute()
    assert path.endswith("tax_microdata_2024.csv")
    assert components["assistant"]["usage_db_writable"] in (True, False)


def test_scrubber_handles_embedded_paths_and_leaves_urls_alone():
    scrub = api_module._scrub_path_text
    assert scrub(f"could not read {REPO_ROOT}/a/b.csv") == "could not read a/b.csv"
    assert scrub("failed: /home/someone/x/y/data.db busy") == "failed: data.db busy"
    assert scrub("https://www.cbo.gov/system/files/x.pdf and/or /readiness") == (
        "https://www.cbo.gov/system/files/x.pdf and/or /readiness"
    )
    assert scrub("FY2026/2027 >=3.10,<3.14") == "FY2026/2027 >=3.10,<3.14"


def _report(label: str) -> ReadinessReport:
    checks = [
        ReadinessCheck(
            name="runtime",
            status="pass",
            required=True,
            summary=f"Runtime ok ({label}) at {REPO_ROOT}/fiscal_model.",
            details={
                "python_version": "3.12.0",
                "executable": sys.executable,
                "api_key_configured": True,
                "path": f"{REPO_ROOT}/fiscal_model/x.csv",
            },
        )
    ]
    return ReadinessReport(
        verdict="ready",
        generated_at="2026-04-01T00:00:00Z",
        pass_count=1,
        warn_count=0,
        fail_count=0,
        checks=checks,
        issues=[],
    )


def test_readiness_is_scrubbed_and_cached(monkeypatch):
    calls = []

    def builder():
        calls.append(1)
        return _report(f"call {len(calls)}")

    clock = {"now": 1000.0}
    monkeypatch.setattr(api_module, "build_readiness_report", builder)
    monkeypatch.setattr(api_module, "_now", lambda: clock["now"])
    api_module._clear_readiness_cache()
    try:
        client = _client()
        first = client.get("/readiness")
        second = client.get("/readiness")
        assert first.status_code == second.status_code == 200
        assert len(calls) == 1  # the second request cost nothing
        assert first.json() == second.json()
        _assert_no_host_details(json.dumps(first.json()))
        details = first.json()["checks"][0]["details"]
        assert details["python_version"] == "3.12.0"
        assert details["path"] == "fiscal_model/x.csv"

        clock["now"] += api_module.READINESS_CACHE_SECONDS - 1
        client.get("/readiness")
        assert len(calls) == 1  # still inside the window

        clock["now"] += 2
        refreshed = client.get("/readiness")
        assert len(calls) == 2  # expired: one fresh run
        assert "call 2" in refreshed.json()["checks"][0]["summary"]
    finally:
        api_module._clear_readiness_cache()


def test_a_replaced_builder_never_sees_anothers_cached_report(monkeypatch):
    api_module._clear_readiness_cache()
    try:
        monkeypatch.setattr(api_module, "build_readiness_report", lambda: _report("A"))
        assert "(A)" in _client().get("/readiness").json()["checks"][0]["summary"]
        monkeypatch.setattr(api_module, "build_readiness_report", lambda: _report("B"))
        assert "(B)" in _client().get("/readiness").json()["checks"][0]["summary"]
    finally:
        api_module._clear_readiness_cache()


def test_the_cli_still_reports_full_detail():
    """The scrub is at the API boundary only; the CLI's report is untouched."""
    from fiscal_model.readiness import build_readiness_report

    report = build_readiness_report()
    runtime = next(c for c in report.checks if c.name == "runtime")
    assert runtime.details.get("executable")
