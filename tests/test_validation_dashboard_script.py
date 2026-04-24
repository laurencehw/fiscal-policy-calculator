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
    for key in ("baseline", "fred", "irs_soi", "model", "microdata", "overall"):
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
    assert "health" in payload
    assert "calibration" in payload
    assert "summary" in payload["calibration"]
