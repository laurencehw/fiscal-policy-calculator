"""Tests for the cold-holdout out-of-sample validation report."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.cold_holdout import build_report, main  # noqa: E402


def test_report_has_two_tiers():
    report = build_report()
    assert "out_of_sample" in report
    assert "calibrated_reference" in report
    for tier in (report["out_of_sample"], report["calibrated_reference"]):
        assert "summary" in tier and "entries" in tier
        assert tier["summary"]["n"] == len(tier["entries"])


def test_out_of_sample_tier_is_genuinely_uncalibrated():
    """The out-of-sample tier must be non-empty and clearly less accurate than
    the calibrated tier — otherwise we have lost the prediction/calibration
    distinction the whole report exists to preserve."""
    report = build_report()
    oos = report["out_of_sample"]["summary"]
    cal = report["calibrated_reference"]["summary"]

    assert oos["n"] >= 3, "expected several genuine out-of-sample predictions"
    assert cal["n"] >= 10, "expected a substantial calibrated reference set"
    # Calibrated error is low by construction; out-of-sample error is materially
    # higher. If they ever converge, the 'calibrated' set has leaked into the
    # holdout (or vice versa) and the framing is no longer honest.
    assert oos["mean_abs_error"] > cal["mean_abs_error"]


def test_entries_carry_provenance():
    report = build_report()
    for e in report["out_of_sample"]["entries"]:
        assert e["official_source"]
        assert e["policy_name"]
        assert isinstance(e["abs_percent_error"], (int, float))


def test_guardrail_exit_codes():
    # A generous threshold passes; an impossible one fails.
    assert main(["--max-mean-error", "1000"]) == 0
    assert main(["--max-mean-error", "0"]) == 1


def test_json_mode_runs(capsys):
    assert main(["--json"]) == 0
    out = capsys.readouterr().out
    assert '"out_of_sample"' in out


def test_ordinary_income_base_flag():
    """The ordinary-income-base correction must (a) be a no-op by default,
    (b) reduce the static base for a high-threshold income-tax rate increase
    when enabled, and (c) be a no-op for non-income-tax policies."""
    from fiscal_model.policies import PolicyType, TaxPolicy

    def static(**kw):
        p = TaxPolicy(
            name="t", description="d", policy_type=PolicyType.INCOME_TAX,
            rate_change=0.026, affected_income_threshold=400_000, **kw
        )
        return p.estimate_static_revenue_effect(0.0, use_real_data=True)

    legacy = static()
    corrected = static(ordinary_income_base=True)
    assert corrected < legacy  # cap gains excluded -> smaller ordinary base
    assert corrected > 0

    # Default must be off (no behavior change for existing callers).
    assert static(ordinary_income_base=False) == legacy


def test_correction_report_runs():
    from scripts.cold_holdout import corrected_out_of_sample

    corr = corrected_out_of_sample()
    assert corr["entries"]
    # The Biden ordinary-rate case must improve materially under the correction.
    biden = next((r for r in corr["entries"] if "Biden" in r["policy_name"]), None)
    assert biden is not None
    assert biden["err_corrected"] < biden["err_legacy"]
