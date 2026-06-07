#!/usr/bin/env python3
"""
Cold-holdout report: the model's genuine out-of-sample accuracy.

The headline validation table mixes two epistemically different things:

* **Calibrated reference models** (TCJA, Corporate, Estate, Credits, AMT, …):
  specialized modules whose parameters are tuned so their components reproduce
  the published CBO/JCT/Treasury decomposition. Low error is expected *by
  construction* — they are transparent reconstructions of official scores, not
  independent confirmations of the model's predictive power.

* **Uncalibrated predictions** (the "Generic" runner): policies scored purely
  bottom-up from IRS SOI filer counts and incomes via raw rate/threshold
  auto-population, with **no fitting to the official target**. This is the only
  tier that measures genuine out-of-sample accuracy.

This script runs the live scorecard and reports the two tiers separately, so
the genuine prediction error is stated plainly (and never goes stale in the
docs). It is the reproducible source for the "Out-of-sample" table in
``README.md`` and ``docs/VALIDATION.md``.

Usage:
    python scripts/cold_holdout.py
    python scripts/cold_holdout.py --json
    python scripts/cold_holdout.py --max-mean-error 35   # CI guardrail
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.validation.scorecard import compute_scorecard  # noqa: E402

UNCALIBRATED_CATEGORY = "Generic"


def build_report() -> dict:
    """Partition the live scorecard into uncalibrated vs calibrated tiers."""
    summary = compute_scorecard()

    def _entry_dict(e) -> dict:
        return {
            "policy_id": e.policy_id,
            "policy_name": e.policy_name,
            "official_10yr_billions": round(e.official_10yr_billions, 1),
            "model_10yr_billions": round(e.model_10yr_billions, 1),
            "abs_percent_error": round(e.abs_percent_difference, 1),
            "direction_match": e.direction_match,
            "official_source": e.official_source,
            "benchmark_date": e.benchmark_date,
        }

    uncal = [e for e in summary.entries if e.category == UNCALIBRATED_CATEGORY]
    cal = [e for e in summary.entries if e.category != UNCALIBRATED_CATEGORY]

    def _agg(entries) -> dict:
        if not entries:
            return {"n": 0, "mean_abs_error": 0.0, "median_abs_error": 0.0, "within_15pct": 0}
        errs = sorted(e.abs_percent_difference for e in entries)
        mid = len(errs) // 2
        median = errs[mid] if len(errs) % 2 else (errs[mid - 1] + errs[mid]) / 2
        return {
            "n": len(errs),
            "mean_abs_error": round(sum(errs) / len(errs), 1),
            "median_abs_error": round(median, 1),
            "within_15pct": sum(1 for e in errs if e <= 15.0),
        }

    return {
        "out_of_sample": {
            "summary": _agg(uncal),
            "entries": [_entry_dict(e) for e in sorted(uncal, key=lambda x: x.abs_percent_difference)],
        },
        "calibrated_reference": {
            "summary": _agg(cal),
            "entries": [_entry_dict(e) for e in sorted(cal, key=lambda x: x.abs_percent_difference)],
        },
    }


def corrected_out_of_sample() -> dict:
    """Re-score the out-of-sample income-tax cases with the ``ordinary_income_base``
    correction (exclude preferentially-taxed capital gains from an ordinary-rate
    change) and report the new error alongside the legacy number.

    This is a *uniform* correction applied to every case — not per-case tuning.
    It is the more economically correct treatment for pure ordinary-rate changes;
    AGI-inclusive surtaxes would set the flag False.
    """
    from fiscal_model.scoring import FiscalPolicyScorer
    from fiscal_model.validation.cbo_scores import KNOWN_SCORES
    from fiscal_model.validation.core import create_policy_from_score

    base = build_report()["out_of_sample"]["entries"]
    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=True)

    rows = []
    for e in base:
        score = KNOWN_SCORES.get(e["policy_id"])
        if score is None:
            continue
        policy = create_policy_from_score(score, ordinary_income_base=True)
        if policy is None:
            continue
        model = scorer.score_policy(policy, dynamic=False).total_10_year_cost
        official = e["official_10yr_billions"]
        err = abs((model - official) / official * 100) if official else 0.0
        rows.append(
            {
                "policy_name": e["policy_name"],
                "official_10yr_billions": official,
                "model_legacy": e["model_10yr_billions"],
                "err_legacy": e["abs_percent_error"],
                "model_corrected": round(model, 1),
                "err_corrected": round(err, 1),
            }
        )

    def _mean(key):
        vals = [r[key] for r in rows]
        return round(sum(vals) / len(vals), 1) if vals else 0.0

    return {
        "entries": rows,
        "mean_err_legacy": _mean("err_legacy"),
        "mean_err_corrected": _mean("err_corrected"),
    }


def _print_human(report: dict) -> None:
    oos = report["out_of_sample"]
    cal = report["calibrated_reference"]

    print("=" * 72)
    print("COLD HOLDOUT - genuine out-of-sample accuracy (uncalibrated predictions)")
    print("=" * 72)
    s = oos["summary"]
    print(
        f"  {s['n']} policies scored bottom-up from IRS SOI, no target fitting.\n"
        f"  Mean abs error: {s['mean_abs_error']}%   "
        f"Median: {s['median_abs_error']}%   "
        f"Within 15%: {s['within_15pct']}/{s['n']}"
    )
    print()
    print(f"  {'Policy':<34}{'Official':>10}{'Model':>10}{'Err':>7}  Source")
    print("  " + "-" * 70)
    for e in oos["entries"]:
        print(
            f"  {e['policy_name'][:33]:<34}"
            f"{e['official_10yr_billions']:>+10.0f}"
            f"{e['model_10yr_billions']:>+10.0f}"
            f"{e['abs_percent_error']:>6.0f}%  {e['official_source']}"
        )
    print()
    print("-" * 72)
    print("CALIBRATED REFERENCE MODELS (low error expected by construction)")
    print("-" * 72)
    c = cal["summary"]
    print(
        f"  {c['n']} policies | mean abs error {c['mean_abs_error']}% | "
        f"within 15%: {c['within_15pct']}/{c['n']}"
    )
    print(
        "  These are tuned to reproduce published CBO/JCT decompositions; they\n"
        "  demonstrate the model's structure, not independent predictive accuracy."
    )


def _print_correction(corr: dict) -> None:
    print()
    print("-" * 72)
    print("WITH ordinary-income-base correction (exclude preferential cap gains)")
    print("-" * 72)
    print(f"  {'Policy':<34}{'Official':>10}{'Legacy':>9}{'Corr.':>9}  Err legacy->corr")
    print("  " + "-" * 70)
    for r in corr["entries"]:
        print(
            f"  {r['policy_name'][:33]:<34}"
            f"{r['official_10yr_billions']:>+10.0f}"
            f"{r['model_legacy']:>+9.0f}"
            f"{r['model_corrected']:>+9.0f}"
            f"  {r['err_legacy']:>5.0f}% -> {r['err_corrected']:>3.0f}%"
        )
    print()
    print(
        f"  Mean abs error: {corr['mean_err_legacy']}% (legacy)  ->  "
        f"{corr['mean_err_corrected']}% (corrected)"
    )
    print(
        "  Note: the correction is uniform (not per-case tuned). It improves the\n"
        "  two large over-predictions and reveals that the two previously-'good'\n"
        "  cases were accurate via offsetting errors. AGI-inclusive surtaxes\n"
        "  should NOT use it (cap gains are in their base)."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table.")
    parser.add_argument(
        "--ordinary-base",
        action="store_true",
        help="Also show the out-of-sample error with the ordinary-income-base "
        "correction applied (excludes preferential capital gains).",
    )
    parser.add_argument(
        "--max-mean-error",
        type=float,
        default=None,
        help="Exit non-zero if out-of-sample mean abs error exceeds this percent (CI guardrail).",
    )
    args = parser.parse_args(argv)

    report = build_report()
    if args.ordinary_base:
        report["ordinary_base_correction"] = corrected_out_of_sample()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)
        if args.ordinary_base:
            _print_correction(report["ordinary_base_correction"])

    if args.max_mean_error is not None:
        mean_err = report["out_of_sample"]["summary"]["mean_abs_error"]
        if mean_err > args.max_mean_error:
            print(
                f"\nFAIL: out-of-sample mean abs error {mean_err}% "
                f"exceeds threshold {args.max_mean_error}%",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
