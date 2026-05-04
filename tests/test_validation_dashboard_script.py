"""
Smoke test for scripts/run_validation_dashboard.py.

The script is CI-adjacent infrastructure: imports fiscal_model health,
CPS loader, and SOI calibration, and prints a dashboard. We smoke-test
by importing the module, exercising its formatters, and verifying the
JSON path runs end-to-end without raising.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "run_validation_dashboard.py"
)


@pytest.fixture
def dashboard_module():
    """Load the script as a module so we can import its helpers."""
    spec = importlib.util.spec_from_file_location(
        "_run_validation_dashboard_test", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_script_file_exists():
    assert SCRIPT_PATH.exists(), (
        f"Expected script at {SCRIPT_PATH}. "
        "If the dashboard was renamed, update this test."
    )


def test_fmt_billion_handles_none_and_small(dashboard_module):
    assert dashboard_module._fmt_billion(None) == "—"
    assert "B" in dashboard_module._fmt_billion(42.0)
    # Values at or above $1T should render as T.
    assert "T" in dashboard_module._fmt_billion(1500.0)


def test_fmt_pct_handles_none(dashboard_module):
    assert dashboard_module._fmt_pct(None) == "—"
    assert dashboard_module._fmt_pct(73.5) == "73.5%"


def test_collect_health_returns_expected_keys(dashboard_module):
    health = dashboard_module.collect_health()
    for key in ("runtime", "baseline", "fred", "irs_soi", "model", "microdata", "overall"):
        assert key in health, f"Health output missing {key}"


def test_collect_microdata_returns_descriptor_and_report(dashboard_module):
    collected = dashboard_module.collect_microdata(2022)
    assert "descriptor" in collected
    # Bundled file is real-CPS so a report should be present.
    assert collected["report"] is not None
    report = collected["report"]
    assert report.year == 2022
    assert len(report.brackets) > 0


def test_json_mode_produces_valid_json(dashboard_module, capsys, monkeypatch):
    """Run ``main`` in --json mode and verify the output parses."""
    monkeypatch.setattr(sys, "argv", ["dashboard", "--json"])
    exit_code = dashboard_module.main()
    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["overall"] in {"ok", "warn", "fail"}
    assert "generated_at" in payload
    assert payload["gates"].keys() >= {
        "health",
        "calibration",
        "distributional_benchmarks",
    }
    assert "health" in payload
    assert "calibration" in payload
    assert "augmentation" in payload["calibration"]
    assert "filter" in payload["calibration"]
    assert "summary" in payload["calibration"]
    assert "issues" in payload
    assert isinstance(payload["issues"], list)


def test_json_mode_records_augmentation_metadata(dashboard_module, capsys, monkeypatch):
    """Augmented dashboard artifacts should disclose the synthetic top-tail run."""
    monkeypatch.setattr(sys, "argv", ["dashboard", "--json", "--augment-top-tail"])
    exit_code = dashboard_module.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    augmentation = payload["calibration"]["augmentation"]
    assert augmentation is not None
    assert augmentation["synthetic_records"] > 0
    assert augmentation["synthetic_weight"] > 0
    assert augmentation["synthetic_agi_billions"] > 0


def test_environmental_fred_fallback_does_not_fail_gate(dashboard_module):
    """FRED in fallback mode (no API key) is env-ok, not a failure."""
    info = {"status": "degraded", "source": "fallback", "error": None}
    assert dashboard_module._is_environmental_degradation("fred", info) is True


def test_environmental_baseline_irs_proxy_does_not_fail_gate(dashboard_module):
    """Baseline GDP proxy when FRED is down is env-ok, not a failure."""
    info = {
        "status": "degraded",
        "gdp_source": "irs_ratio_proxy",
        "load_error": None,
    }
    assert dashboard_module._is_environmental_degradation("baseline", info) is True


def test_real_fred_error_does_fail_gate(dashboard_module):
    """A FRED error (not just fallback) should still fail the gate."""
    info = {"status": "error", "source": None, "error": "connection refused"}
    assert dashboard_module._is_environmental_degradation("fred", info) is False


def test_stale_bundled_fred_seed_fails_gate(dashboard_module):
    """Stale tracked seed data is repo maintenance, not an env fallback."""
    info = {
        "status": "degraded",
        "source": "bundled",
        "cache_is_expired": True,
    }
    assert dashboard_module._is_environmental_degradation("fred", info) is False


def test_model_degradation_always_fails_gate(dashboard_module):
    """A scoring-engine error is always a real regression."""
    info = {"status": "error", "error": "something broke"}
    assert dashboard_module._is_environmental_degradation("model", info) is False


def test_json_gate_helpers_distinguish_warn_and_fail_paths(dashboard_module):
    assert dashboard_module.benchmarks_gate_ok([
        {"policy_id": "ok", "rating": "excellent"},
    ]) is True
    assert dashboard_module.benchmarks_gate_ok([
        {"policy_id": "bad", "rating": "needs_improvement"},
    ]) is False
    assert dashboard_module.benchmarks_gate_ok([{"error": "boom"}]) is False

    assert dashboard_module.health_gate_ok({
        "runtime": {"status": "ok"},
        "baseline": {"status": "ok"},
        "fred": {"status": "degraded", "source": "fallback"},
        "irs_soi": {"status": "ok"},
        "model": {"status": "ok"},
        "microdata": {"status": "ok"},
    }) is True
    assert dashboard_module.health_gate_ok({
        "runtime": {"status": "degraded"},
    }) is False


def test_health_gate_issues_report_non_environmental_failures(dashboard_module):
    health = {
        "runtime": {
            "status": "degraded",
            "python_version": "3.14.0",
            "supported_range": ">=3.10,<3.14",
            "message": "Python 3.14.0 is unsupported.",
        },
        "baseline": {"status": "degraded", "gdp_source": "irs_ratio_proxy"},
        "fred": {"status": "degraded", "source": "fallback"},
        "irs_soi": {"status": "ok"},
        "model": {"status": "ok"},
        "microdata": {"status": "ok"},
    }

    issues = dashboard_module.health_gate_issues(health)

    assert len(issues) == 1
    assert issues[0]["surface"] == "health"
    assert issues[0]["component"] == "runtime"
    assert issues[0]["severity"] == "fail"
    assert "unsupported" in issues[0]["message"]


def test_calibration_gate_issues_report_zero_top_bracket(dashboard_module):
    report = SimpleNamespace(
        brackets=[
            SimpleNamespace(
                lower=0.0,
                upper=1_000_000.0,
                returns_ratio=1.0,
                agi_ratio=1.0,
            ),
            SimpleNamespace(
                lower=1_000_000.0,
                upper=None,
                returns_ratio=0.0,
                agi_ratio=0.0,
            ),
        ]
    )
    calibration = {"descriptor": {"status": "real"}, "report": report}

    issues = dashboard_module.calibration_gate_issues(calibration)

    assert dashboard_module.calibration_gate_ok(calibration) is False
    assert len(issues) == 1
    assert issues[0]["surface"] == "calibration"
    assert issues[0]["severity"] == "warn"
    assert issues[0]["lower"] == 1_000_000.0
    assert issues[0]["upper"] is None
    assert issues[0]["agi_ratio"] == 0.0
    assert issues[0]["threshold"] == 0.60


def test_benchmark_gate_issues_report_errors_and_bad_ratings(dashboard_module):
    issues = dashboard_module.benchmark_gate_issues([
        {"policy_id": "bad", "rating": "needs_improvement"},
        {"error": "runner crashed"},
    ])

    assert len(issues) == 2
    assert {issue["surface"] for issue in issues} == {"distributional_benchmarks"}
    assert {issue["severity"] for issue in issues} == {"fail"}
    assert any(issue.get("policy_id") == "bad" for issue in issues)
    assert any("runner crashed" in issue["message"] for issue in issues)


def test_print_health_fails_on_unsupported_runtime(dashboard_module, capsys):
    """Unsupported Python versions should trip the release-readiness gate."""
    health = {
        "runtime": {
            "status": "degraded",
            "python_version": "3.14.0",
            "supported_range": ">=3.10,<3.14",
        },
        "baseline": {"status": "ok", "vintage": "February 2026"},
        "fred": {"status": "ok", "source": "live"},
        "irs_soi": {"status": "ok", "latest_year": 2022},
        "model": {"status": "ok", "test_score": -1.0},
        "microdata": {
            "status": "ok",
            "calibration_year": 2022,
            "returns_coverage_pct": 100.0,
            "agi_coverage_pct": 100.0,
        },
        "overall": "degraded",
    }

    assert dashboard_module.print_health(health) is False
    out = capsys.readouterr().out
    assert "runtime" in out
    assert "3.14.0" in out
