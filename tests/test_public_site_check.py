"""
Tests for scripts/check_public_site.py, the uptime check for the Next.js site.
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_public_site.py"


@pytest.fixture
def site_check():
    spec = importlib.util.spec_from_file_location("_public_site_check_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _response(text="", payload=None, status_error=None):
    def raise_for_status():
        if status_error is not None:
            raise status_error

    def json():
        if payload is None:
            raise ValueError("not JSON")
        return payload

    return SimpleNamespace(text=text, raise_for_status=raise_for_status, json=json)


def _healthy(monkeypatch, site_check, score_payload=None):
    pages = {f"https://site.test{path}": marker for path, marker in site_check.PAGES}
    monkeypatch.setattr(
        site_check.requests, "get", lambda url, **kw: _response(f"<html>{pages[url]}</html>")
    )
    payload = {"ten_year_deficit_impact": -116.2} if score_payload is None else score_payload
    monkeypatch.setattr(site_check.requests, "post", lambda url, **kw: _response(payload=payload))


def test_healthy_site_passes_every_check(site_check, monkeypatch):
    _healthy(monkeypatch, site_check)
    report = site_check.build_report("https://site.test", 5)
    assert report["overall"] == "ok"
    assert len(report["checks"]) == len(site_check.PAGES) + 1
    assert "-116.2B" in report["checks"][-1]["message"]


def test_a_page_without_its_marker_fails(site_check, monkeypatch):
    _healthy(monkeypatch, site_check)
    monkeypatch.setattr(site_check.requests, "get", lambda url, **kw: _response("<html>Application error</html>"))
    report = site_check.build_report("https://site.test", 5)
    assert report["overall"] == "failed"
    assert all(i["surface"] == "public_site" for i in report["issues"])
    assert len(report["issues"]) == len(site_check.PAGES)


def test_score_without_a_number_fails(site_check, monkeypatch):
    _healthy(monkeypatch, site_check, score_payload={"error": "Live scoring is not connected yet."})
    report = site_check.build_report("https://site.test", 5)
    assert report["overall"] == "failed"
    assert report["issues"][0]["url"].endswith("/api/score")


def test_http_errors_are_reported_not_raised(site_check, monkeypatch):
    _healthy(monkeypatch, site_check)

    def boom(url, **kw):
        raise requests.ConnectionError("unreachable")

    monkeypatch.setattr(site_check.requests, "post", boom)
    report = site_check.build_report("https://site.test", 5)
    assert report["overall"] == "failed"
    assert "unreachable" in report["issues"][0]["message"]
