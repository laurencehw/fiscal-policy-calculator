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


def test_microdata_coverage_overcount_warns_instead_of_failing(dashboard_module):
    """Overcount-only coverage (e.g. 119% of SOI returns) is a bundled-data
    quality signal: never a green check, but not a per-PR gate failure."""
    health = {
        "runtime": {"status": "ok"},
        "baseline": {"status": "ok"},
        "fred": {"status": "ok", "source": "live"},
        "irs_soi": {"status": "ok"},
        "model": {"status": "ok"},
        "microdata": {
            "status": "degraded",
            "returns_coverage_pct": 119.0,
            "agi_coverage_pct": 81.0,
            "coverage_overcount": True,
            "coverage_undercount": False,
        },
    }
    issues = dashboard_module.health_gate_issues(health)
    assert [i["severity"] for i in issues] == ["warn"]
    assert dashboard_module.health_gate_ok(health) is True

    # Undercount stays a hard failure.
    health["microdata"].update(
        {
            "returns_coverage_pct": 60.0,
            "agi_coverage_pct": 55.0,
            "coverage_overcount": False,
            "coverage_undercount": True,
        }
    )
    issues = dashboard_module.health_gate_issues(health)
    assert [i["severity"] for i in issues] == ["fail"]
    assert dashboard_module.health_gate_ok(health) is False


def test_environmental_baseline_fresh_bundled_seed_does_not_fail_gate(dashboard_module):
    """Baseline riding a *fresh* bundled seed is the designed offline mode
    (mirrors the strict readiness gate)."""
    info = {
        "status": "degraded",
        "source": "real_data",
        "gdp_source": "fred_bundled",
        "load_error": None,
        "fred": {"source": "bundled", "cache_is_expired": False, "cache_age_days": 0},
    }
    assert dashboard_module._is_environmental_degradation("baseline", info) is True


def test_baseline_expired_bundled_seed_fails_gate(dashboard_module):
    """An expired seed stays a gate failure — the maintenance signal."""
    info = {
        "status": "degraded",
        "source": "real_data",
        "gdp_source": "fred_bundled",
        "load_error": None,
        "fred": {"source": "bundled", "cache_is_expired": True, "cache_age_days": 150},
    }
    assert dashboard_module._is_environmental_degradation("baseline", info) is False


# ---------------------------------------------------------------------------
# Tier 2 (leave-one-out) section — see fiscal_model/validation/loo.py
# ---------------------------------------------------------------------------


def test_loo_gate_passes_under_the_ceiling(dashboard_module):
    from fiscal_model.validation.loo import run_leave_one_out

    suite = run_leave_one_out()
    ceiling = dashboard_module.DEFAULT_MAX_LOO_MEAN_ERROR
    assert suite.mean_abs_percent_error is not None
    assert suite.mean_abs_percent_error <= ceiling, (
        "Tier 2 (LOO) regressed past its ceiling. This is a structural-machinery "
        "regression signal, not an accuracy claim — see docs/VALIDATION_NOTES.md §6."
    )
    assert dashboard_module.loo_gate_ok(suite, ceiling) is True
    assert dashboard_module.loo_gate_issues(suite, ceiling) == []


def test_loo_gate_fails_above_the_ceiling(dashboard_module):
    from fiscal_model.validation.loo import run_leave_one_out

    suite = run_leave_one_out()
    issues = dashboard_module.loo_gate_issues(suite, 0.5)
    assert len(issues) == 1
    assert issues[0]["surface"] == "loo"
    assert issues[0]["severity"] == "fail"
    assert "ceiling" in issues[0]["message"]
    assert dashboard_module.loo_gate_ok(suite, 0.5) is False


def test_loo_gate_fails_when_the_suite_is_unavailable(dashboard_module):
    assert dashboard_module.loo_gate_ok(None, 75.0) is False
    issues = dashboard_module.loo_gate_issues(None, 75.0)
    assert issues and issues[0]["severity"] == "fail"


def test_print_loo_reports_both_counts(dashboard_module, capsys):
    from fiscal_model.validation.loo import run_leave_one_out

    suite = run_leave_one_out()
    ok = dashboard_module.print_loo(suite, dashboard_module.DEFAULT_MAX_LOO_MEAN_ERROR)
    out = capsys.readouterr().out
    assert ok is True
    assert "Tier 2 (leave-one-out)" in out
    assert "not cross-validatable" in out
    assert f"{len(suite.excluded_cases)}" in out
    # Non-derivable cases are reported but never folded into the aggregate.
    assert f"n={len(suite.included_cases)}" in out


def test_dashboard_json_includes_the_loo_surface(dashboard_module, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_validation_dashboard.py", "--json"])
    assert dashboard_module.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "leave_one_out" in payload
    assert payload["leave_one_out"]["tier"] == "Tier 2 (leave-one-out)"
    assert payload["leave_one_out"]["ceiling"] == (
        dashboard_module.DEFAULT_MAX_LOO_MEAN_ERROR
    )
    assert "leave_one_out" in payload["gates"]


# ── The calibrated tiers ───────────────────────────────────────────────────
#
# ``planning/lanes/SWEEP_offset_sign.md`` §7.5: this whole report came back
# byte-identical across PR #119, a change that moved the fitted tier
# 1.7% -> 1.8% and the reconstruction tier 57.6% -> 57.4%, because the
# dashboard printed Tier 1 and leave-one-out and nothing in between. These
# tests pin the block that closes that, and pin it to ``cold_holdout.py``'s own
# numbers so the two reports cannot drift apart.


def test_calibrated_tiers_match_cold_holdout(dashboard_module):
    """The dashboard must not compute its own answer for either tier."""
    from scripts.cold_holdout import build_report

    tiers = dashboard_module.collect_calibrated_tiers()
    report = build_report()

    assert tiers["fitted"] == report["calibrated_reference"]["summary"]
    assert tiers["reconstruction"] == report["uncalibrated_reconstruction"]["summary"]


def test_held_in_place_puts_back_only_the_revised_fitted_rows(dashboard_module):
    """Held in place is the fitted tier plus the rows a revision moved out.

    Not plus every ``revised_target_entries`` row: most of them are sectoral
    benchmarks the runners never declared fitted, so folding those in would
    report a tier that never existed.
    """
    from fiscal_model.validation import cached_default_scorecard

    tiers = dashboard_module.collect_calibrated_tiers()
    summary = cached_default_scorecard()

    put_back = set(tiers["revised_from_fitted_tier"])
    assert put_back, "expected at least one revised row that had been fitted"
    assert len(put_back) <= tiers["revised_target_entries"]
    assert tiers["fitted_held_in_place"]["n"] == tiers["fitted"]["n"] + len(put_back)

    by_id = {e.policy_id: e for e in summary.entries}
    for policy_id in put_back:
        entry = by_id[policy_id]
        assert entry.target_revision_id is not None
        assert entry.declared_calibrated_to_target is True
        assert entry.calibrated_to_target is False


def test_reconstruction_sub_populations_partition_the_tier(dashboard_module):
    """The tier is several populations and is never quoted as one number."""
    tiers = dashboard_module.collect_calibrated_tiers()
    subs = tiers["reconstruction_sub_populations"]
    assert len(subs) > 1
    assert sum(agg["n"] for agg in subs.values()) == tiers["reconstruction"]["n"]


def test_provenance_counts_come_from_the_scorecard_summary(dashboard_module):
    from fiscal_model.validation import cached_default_scorecard

    tiers = dashboard_module.collect_calibrated_tiers()
    summary = cached_default_scorecard()

    assert tiers["provenance_breakdown"] == dict(summary.provenance_breakdown)
    assert tiers["published_entries"] == summary.published_entries
    assert tiers["transcribed_entries"] == summary.transcribed_entries
    assert tiers["line_item_differs_entries"] == summary.line_item_differs_entries
    assert tiers["model_estimate_entries"] == summary.model_estimate_entries
    assert tiers["revised_target_entries"] == summary.revised_target_entries
    assert sum(summary.provenance_breakdown.values()) == summary.total_entries


def test_print_calibrated_tiers_prints_every_reading(dashboard_module, capsys):
    tiers = dashboard_module.collect_calibrated_tiers()
    dashboard_module.print_calibrated_tiers(tiers)
    out = capsys.readouterr().out

    assert "Calibrated tiers" in out
    assert f"n={tiers['fitted']['n']}" in out
    assert f"mean {tiers['fitted']['mean_abs_error']}%" in out
    assert f"n={tiers['fitted_held_in_place']['n']}" in out
    assert f"mean {tiers['reconstruction']['mean_abs_error']}%" in out
    assert f"revised targets:     {tiers['revised_target_entries']}" in out
    assert "Reconstruction sub-populations" in out
    for category in tiers["reconstruction_sub_populations"]:
        assert category in out
    for label, count in tiers["provenance_breakdown"].items():
        assert f"{label} {count}" in out
    assert f"{tiers['published_entries']}/{tiers['total_entries']}" in out


def test_print_calibrated_tiers_survives_an_unavailable_scorecard(
    dashboard_module, capsys
):
    """Informational blocks report their own failure; they never raise."""
    dashboard_module.print_calibrated_tiers({"error": "scorecard exploded"})
    out = capsys.readouterr().out
    assert "[ERROR]" in out
    assert "scorecard exploded" in out


def test_dashboard_json_includes_the_calibrated_tiers(
    dashboard_module, capsys, monkeypatch
):
    monkeypatch.setattr(sys, "argv", ["run_validation_dashboard.py", "--json"])
    assert dashboard_module.main() == 0
    payload = json.loads(capsys.readouterr().out)

    tiers = payload["calibrated_tiers"]
    assert tiers["fitted"]["n"] > 0
    assert tiers["reconstruction"]["n"] > 0
    assert "fitted_held_in_place" in tiers
    assert "reconstruction_sub_populations" in tiers
    assert "provenance_breakdown" in tiers
    # Informational: it gates nothing.
    assert "calibrated_tiers" not in payload["gates"]
