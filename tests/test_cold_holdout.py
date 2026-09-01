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


def test_out_of_sample_tier_reports_both_accuracy_shares():
    """The headline is 'n cases, mean X%, Y/n within 15%, Z/n within 25%' —
    never a single 'validated within X%' number."""
    summary = build_report()["out_of_sample"]["summary"]
    for key in ("n", "mean_abs_error", "median_abs_error", "within_15pct", "within_25pct"):
        assert key in summary
    assert summary["within_15pct"] <= summary["within_25pct"] <= summary["n"]


def test_out_of_sample_battery_is_wide_enough_to_be_informative():
    """Phase A widened the honest tier from 4 friendly shapes to 9 cases
    spanning ordinary rates, AGI-inclusive surtaxes and capital gains."""
    report = build_report()
    ids = {e["policy_id"] for e in report["out_of_sample"]["entries"]}
    assert len(ids) >= 9
    assert {"biden_capital_gains_39", "top_rate_45", "medicare_surcharge_2pp"} <= ids


def test_poor_out_of_sample_cases_carry_a_documented_reason():
    """A >25% miss is kept in the honest tier, not tuned away — but it has to
    say why it misses, which is also what keeps strict readiness at 'warn'."""
    for entry in build_report()["out_of_sample"]["entries"]:
        if entry["abs_percent_error"] > 25.0:
            assert entry["known_limitations"], (
                f"{entry['policy_id']} misses by "
                f"{entry['abs_percent_error']}% with no known_limitations note"
            )


def test_guardrail_exit_codes():
    # A generous threshold passes; an impossible one fails.
    assert main(["--max-mean-error", "1000"]) == 0
    assert main(["--max-mean-error", "0"]) == 1


def test_within_25pct_floor_guardrail_exit_codes():
    n = build_report()["out_of_sample"]["summary"]["n"]
    assert main(["--min-within-25pct", "0"]) == 0
    assert main(["--min-within-25pct", str(n + 1)]) == 1


def test_json_mode_runs(capsys):
    assert main(["--json"]) == 0
    out = capsys.readouterr().out
    assert '"out_of_sample"' in out


def test_ordinary_income_base_flag():
    """The ordinary-income-base correction must (a) be a no-op by default on
    TaxPolicy, (b) reduce the static base for a high-threshold income-tax rate
    increase when enabled, and (c) be the default for Generic validation via
    create_policy_from_score."""
    from fiscal_model.policies import PolicyType, TaxPolicy
    from fiscal_model.validation.cbo_scores import KNOWN_SCORES
    from fiscal_model.validation.core import create_policy_from_score

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

    # Dataclass default must stay off (explicit opt-in on TaxPolicy itself).
    assert static(ordinary_income_base=False) == legacy

    # Generic validation path defaults to ordinary-income base.
    score = KNOWN_SCORES["biden_high_income_tax"]
    policy = create_policy_from_score(score)
    assert policy is not None
    assert policy.ordinary_income_base is True
    legacy_policy = create_policy_from_score(score, ordinary_income_base=False)
    assert legacy_policy is not None
    assert legacy_policy.ordinary_income_base is False


def test_all_brackets_uses_soi_not_effective_rate_heuristic():
    """threshold=0 must score via SOI taxable income, not baseline×Δrate/0.18."""
    from fiscal_model.policies import PolicyType, TaxPolicy

    policy = TaxPolicy(
        name="1pp all",
        description="uniform 1pp",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=0,
        ordinary_income_base=True,
    )
    # Ridiculous baseline would dominate the old heuristic; SOI path ignores it.
    soi = policy.estimate_static_revenue_effect(50_000.0, use_real_data=True)
    heuristic = 50_000.0 * 1.0 * (0.01 / 0.18)
    assert soi > 0
    assert abs(soi - heuristic) / heuristic > 0.2


def test_correction_report_runs():
    from scripts.cold_holdout import corrected_out_of_sample

    corr = corrected_out_of_sample()
    assert corr["entries"]
    # The Biden ordinary-rate case must improve materially under the correction.
    biden = next((r for r in corr["entries"] if "Biden" in r["policy_name"]), None)
    assert biden is not None
    assert biden["err_corrected"] < biden["err_legacy"]
