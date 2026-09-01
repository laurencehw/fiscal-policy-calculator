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

* **Uncalibrated module reconstructions** (Phase E: the international, trade,
  pharma, enforcement and climate runners): presets carrying an official
  figure whose module holds no constant fitted to it. Reported as their own
  tier — neither a calibration reference nor a bottom-up SOI prediction.
  Provenance is reported alongside, because a handful of those targets are
  themselves model estimates rather than published scores.

This script runs the live scorecard and reports the tiers separately, so
the genuine prediction error is stated plainly (and never goes stale in the
docs). It is the reproducible source for the "Out-of-sample" table in
``README.md`` and ``docs/VALIDATION.md``.

Usage:
    python scripts/cold_holdout.py
    python scripts/cold_holdout.py --json
    python scripts/cold_holdout.py --max-mean-error 60 --min-within-25pct 5  # CI gate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.validation.preregistered import live_cases  # noqa: E402
from fiscal_model.validation.scorecard import compute_scorecard  # noqa: E402

UNCALIBRATED_CATEGORY = "Generic"


def build_report() -> dict:
    """Partition the live scorecard into uncalibrated vs calibrated tiers."""
    summary = compute_scorecard()

    registered = live_cases()

    def _entry_dict(e) -> dict:
        row = {
            "policy_id": e.policy_id,
            "policy_name": e.policy_name,
            "official_10yr_billions": round(e.official_10yr_billions, 1),
            "model_10yr_billions": round(e.model_10yr_billions, 1),
            "abs_percent_error": round(e.abs_percent_difference, 1),
            "direction_match": e.direction_match,
            "official_source": e.official_source,
            "benchmark_date": e.benchmark_date,
            "provenance": getattr(e, "provenance", "unclassified"),
            "calibrated_to_target": getattr(e, "calibrated_to_target", True),
            "known_limitations": list(e.known_limitations),
        }
        case = registered.get(e.policy_id)
        if case is not None:
            row["preregistered"] = {
                "case_id": case.case_id,
                "source_baseline_vintage": case.source_baseline_vintage,
                "entered_commit": case.entered_commit,
                "entered_date": case.entered_date,
                "first_scoring_run_commit": case.first_scoring_run_commit,
            }
        return row

    uncal = [e for e in summary.entries if e.category == UNCALIBRATED_CATEGORY]
    specialized = [e for e in summary.entries if e.category != UNCALIBRATED_CATEGORY]
    # Phase E split the specialized tier in two. Entries whose module carries a
    # constant *fitted* to the benchmark are the calibrated reference set, whose
    # low error is expected by construction. Entries added by the sectoral
    # runners (international, trade, pharma, enforcement, climate) are scored
    # against figures their modules were never fitted to, so folding them into
    # the calibrated mean would misdescribe both tiers.
    cal = [e for e in specialized if getattr(e, "calibrated_to_target", True)]
    recon = [e for e in specialized if not getattr(e, "calibrated_to_target", True)]

    def _agg(entries) -> dict:
        if not entries:
            return {
                "n": 0,
                "mean_abs_error": 0.0,
                "median_abs_error": 0.0,
                "within_15pct": 0,
                "within_25pct": 0,
                "model_estimate_targets": 0,
            }
        errs = sorted(e.abs_percent_difference for e in entries)
        mid = len(errs) // 2
        median = errs[mid] if len(errs) % 2 else (errs[mid - 1] + errs[mid]) / 2
        return {
            "n": len(errs),
            "mean_abs_error": round(sum(errs) / len(errs), 1),
            "median_abs_error": round(median, 1),
            "within_15pct": sum(1 for e in errs if e <= 15.0),
            "within_25pct": sum(1 for e in errs if e <= 25.0),
            # Not every target in a tier is a published score. Carrying the
            # count here stops the human summary from claiming more provenance
            # than the tier actually has.
            "model_estimate_targets": sum(
                1
                for e in entries
                if getattr(e, "provenance", "unclassified") == "model_estimate"
            ),
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
        "uncalibrated_reconstruction": {
            "summary": _agg(recon),
            "entries": [
                _entry_dict(e)
                for e in sorted(recon, key=lambda x: x.abs_percent_difference)
            ],
        },
    }


def corrected_out_of_sample() -> dict:
    """Compare legacy whole-base scoring vs ordinary-income-base for OOS cases.

    Production Generic scoring now defaults to ``ordinary_income_base=True``.
    This report still contrasts the old whole-base path (explicit False) against
    the current default so the structural correction remains auditable.
    """
    from fiscal_model.scoring import FiscalPolicyScorer
    from fiscal_model.validation.cbo_scores import KNOWN_SCORES, validation_shape
    from fiscal_model.validation.core import create_policy_from_score

    base = build_report()["out_of_sample"]["entries"]
    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=True)

    rows = []
    for e in base:
        score = KNOWN_SCORES.get(e["policy_id"])
        if score is None:
            continue
        # The ordinary-income-base flag only exists on the ordinary-rate shape;
        # capital-gains and spending shapes have no such switch.
        if validation_shape(score) != "ordinary_rate":
            continue
        legacy_policy = create_policy_from_score(score, ordinary_income_base=False)
        corrected_policy = create_policy_from_score(score, ordinary_income_base=True)
        if legacy_policy is None or corrected_policy is None:
            continue
        model_legacy = scorer.score_policy(legacy_policy, dynamic=False).total_10_year_cost
        model_corrected = scorer.score_policy(
            corrected_policy, dynamic=False
        ).total_10_year_cost
        official = e["official_10yr_billions"]
        err_legacy = (
            abs((model_legacy - official) / official * 100) if official else 0.0
        )
        err_corrected = (
            abs((model_corrected - official) / official * 100) if official else 0.0
        )
        rows.append(
            {
                "policy_name": e["policy_name"],
                "official_10yr_billions": official,
                "model_legacy": round(model_legacy, 1),
                "err_legacy": round(err_legacy, 1),
                "model_corrected": round(model_corrected, 1),
                "err_corrected": round(err_corrected, 1),
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
        f"  {s['n']} out-of-sample cases, mean abs error {s['mean_abs_error']}%, "
        f"{s['within_15pct']}/{s['n']} within 15%, "
        f"{s['within_25pct']}/{s['n']} within 25%.\n"
        f"  Scored bottom-up from IRS SOI with no target fitting; every case is "
        f"pre-registered in\n  fiscal_model/validation/preregistered.py. "
        f"Median abs error: {s['median_abs_error']}%."
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
        f"within 15%: {c['within_15pct']}/{c['n']} | "
        f"within 25%: {c['within_25pct']}/{c['n']}"
    )
    print(
        "  These are tuned to reproduce their targets; they demonstrate the\n"
        "  model's structure, not independent predictive accuracy."
    )
    model_est = c.get("model_estimate_targets", 0)
    if model_est:
        print(
            f"  {c['n'] - model_est} of them reproduce a published CBO/JCT/Treasury"
            " decomposition. The\n"
            f"  other {model_est} are fitted to a target that is itself a model"
            " estimate\n  (provenance = model_estimate), so those measure internal"
            " consistency only."
        )

    reconstruction = report.get("uncalibrated_reconstruction")
    if reconstruction and reconstruction["summary"]["n"]:
        r = reconstruction["summary"]
        print()
        print("-" * 72)
        print("UNCALIBRATED MODULE RECONSTRUCTIONS (target not fitted to)")
        print("-" * 72)
        print(
            f"  {r['n']} policies | mean abs error {r['mean_abs_error']}% | "
            f"within 15%: {r['within_15pct']}/{r['n']} | "
            f"within 25%: {r['within_25pct']}/{r['n']}"
        )
        print(
            "  Sectoral modules (international, trade, pharma, enforcement,"
            " climate)\n  scored against targets they were never fitted to."
            " Large misses here are\n  findings about those modules; each"
            " carries a known-limitations note and\n  none was retuned."
        )
        r_model_est = r.get("model_estimate_targets", 0)
        if r_model_est:
            print(
                f"  {r_model_est} of the {r['n']} targets are model estimates rather"
                " than published\n  scores (provenance = model_estimate)."
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
    parser.add_argument(
        "--min-within-25pct",
        type=int,
        default=None,
        help="Exit non-zero if fewer than this many out-of-sample cases land within "
        "25%% of their official target (CI guardrail).",
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

    summary = report["out_of_sample"]["summary"]
    failed = False

    if args.max_mean_error is not None:
        mean_err = summary["mean_abs_error"]
        if mean_err > args.max_mean_error:
            print(
                f"\nFAIL: out-of-sample mean abs error {mean_err}% "
                f"exceeds threshold {args.max_mean_error}%",
                file=sys.stderr,
            )
            failed = True

    if args.min_within_25pct is not None:
        within_25 = summary["within_25pct"]
        if within_25 < args.min_within_25pct:
            print(
                f"\nFAIL: only {within_25}/{summary['n']} out-of-sample cases are within "
                f"25% of their official target; floor is {args.min_within_25pct}",
                file=sys.stderr,
            )
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
