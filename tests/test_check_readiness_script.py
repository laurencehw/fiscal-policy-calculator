"""
Smoke tests for scripts/check_readiness.py.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from fiscal_model.readiness import (
    ReadinessCheck,
    ReadinessReport,
    readiness_issues_from_checks,
)

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_readiness.py"


@pytest.fixture
def readiness_script():
    spec = importlib.util.spec_from_file_location("_check_readiness_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _report(verdict: str) -> ReadinessReport:
    if verdict == "not_ready":
        status = "fail"
    elif verdict == "ready_with_warnings":
        status = "warn"
    else:
        status = "pass"
    checks = [
        ReadinessCheck(
            name="runtime",
            status="pass",
            required=True,
            summary="Runtime ok.",
        ),
        ReadinessCheck(
            name="gate",
            status=status,
            required=(verdict == "not_ready"),
            summary="Gate status.",
        ),
    ]
    return ReadinessReport(
        verdict=verdict,
        generated_at="2026-04-01T00:00:00Z",
        pass_count=2 if verdict == "ready" else 1,
        warn_count=1 if verdict == "ready_with_warnings" else 0,
        fail_count=1 if verdict == "not_ready" else 0,
        checks=checks,
        issues=readiness_issues_from_checks(checks),
    )


def _environmental_warning_report() -> ReadinessReport:
    checks = [
        ReadinessCheck(
            name="runtime",
            status="pass",
            required=True,
            summary="Runtime ok.",
        ),
        ReadinessCheck(
            name="baseline",
            status="warn",
            required=True,
            summary="CBO baseline is using a degraded data path.",
            details={
                "status": "degraded",
                "source": "real_data",
                "gdp_source": "irs_ratio_proxy",
                "load_error": None,
                "fred": {"source": "fallback"},
            },
        ),
        ReadinessCheck(
            name="fred",
            status="warn",
            required=False,
            summary="FRED is using a degraded external-data path.",
            details={"status": "degraded", "source": "fallback"},
        ),
    ]
    return ReadinessReport(
        verdict="ready_with_warnings",
        generated_at="2026-04-01T00:00:00Z",
        pass_count=1,
        warn_count=2,
        fail_count=0,
        checks=checks,
        issues=readiness_issues_from_checks(checks),
    )


def test_script_file_exists():
    assert SCRIPT_PATH.exists()


def test_ready_with_warnings_exits_zero_by_default(readiness_script, monkeypatch, capsys):
    monkeypatch.setattr(readiness_script, "build_readiness_report", lambda: _report("ready_with_warnings"))
    monkeypatch.setattr(sys, "argv", ["check_readiness"])

    assert readiness_script.main() == 0
    out = capsys.readouterr().out
    assert "ready_with_warnings" in out
    assert "Issues:" in out
    assert "Gate status." in out


def test_strict_mode_fails_non_environmental_warnings(readiness_script, monkeypatch):
    monkeypatch.setattr(readiness_script, "build_readiness_report", lambda: _report("ready_with_warnings"))
    monkeypatch.setattr(sys, "argv", ["check_readiness", "--strict"])

    assert readiness_script.main() == 2


def test_strict_mode_allows_environmental_data_warnings(readiness_script, monkeypatch):
    monkeypatch.setattr(readiness_script, "build_readiness_report", _environmental_warning_report)
    monkeypatch.setattr(sys, "argv", ["check_readiness", "--strict"])

    assert readiness_script.main() == 0


def test_not_ready_exits_one(readiness_script, monkeypatch):
    monkeypatch.setattr(readiness_script, "build_readiness_report", lambda: _report("not_ready"))
    monkeypatch.setattr(sys, "argv", ["check_readiness"])

    assert readiness_script.main() == 1


def test_json_output_is_valid(readiness_script, monkeypatch, capsys):
    monkeypatch.setattr(readiness_script, "build_readiness_report", lambda: _report("ready"))
    monkeypatch.setattr(sys, "argv", ["check_readiness", "--json"])

    assert readiness_script.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "ready"
    assert payload["checks"][0]["name"] == "runtime"
    assert payload["issues"] == []
