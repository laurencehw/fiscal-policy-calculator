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
  pharma, enforcement and climate runners; Phase D: the P.L. 119-21 JCT line
  items): targets carrying an official figure whose module holds no constant
  fitted to it. Reported as their own tier — neither a calibration reference
  nor a bottom-up SOI prediction. Provenance is reported alongside, because a
  handful of those targets are themselves model estimates rather than
  published scores, while the P.L. 119-21 block is the only one whose targets
  are individual rows of a published table.

This script runs the live scorecard and reports the tiers separately, so
the genuine prediction error is stated plainly (and never goes stale in the
docs). It is the reproducible source for the "Out-of-sample" table in
``README.md`` and ``docs/VALIDATION.md``.

Usage:
    python scripts/cold_holdout.py
    python scripts/cold_holdout.py --json
    python scripts/cold_holdout.py --max-mean-error 60 --min-within-25pct 5  # CI gate
    python scripts/cold_holdout.py --max-class-mean-error corporate=56 ...   # per-class floor
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.validation.cbo_options import runnable_score_ids  # noqa: E402
from fiscal_model.validation.cbo_scores import KNOWN_SCORES  # noqa: E402
from fiscal_model.validation.preregistered import live_cases  # noqa: E402
from fiscal_model.validation.scorecard import (  # noqa: E402
    GENERIC_CATEGORY,
    compute_scorecard,
)

#: The scorecard's own name for the out-of-sample tier. Aliased rather than
#: re-spelled so a rename of the tier cannot silently split this report in two.
UNCALIBRATED_CATEGORY = GENERIC_CATEGORY

# --------------------------------------------------------------------------
# Policy classes
# --------------------------------------------------------------------------
# ``planning/HIGH_STAKES_ACCURACY.md`` §2 reports Tier 1 as eight populations
# rather than one, because the pooled mean cannot see a class regressing while
# the mean improves -- which is exactly what happened to
# ``medicare_surcharge_2pp`` in Wave 7, and again to
# ``warren_ultramillionaire_surtax_3pp`` in Wave B. §3 process rule 4 asks for a
# per-class floor in CI, so the classification has to live in the tree rather
# than in a lane's spreadsheet.
#
# It is **derived from each case's own ``CBOScore`` record**, never from a
# hand-maintained list of policy ids, so a row registered tomorrow is classified
# the moment it is registered and cannot quietly escape the gate. The rules,
# which reproduce §2's table exactly (6 / 4 / 4 / 1 / 3 / 5 / 2 / 1 on the
# post-Wave-B battery):
#
#   * ``policy_type`` alone settles corporate, payroll, tax-expenditure and
#     capital-gains rows;
#   * an ``income_tax`` row splits on ``agi_inclusive_base`` -- the flag each
#     record already carries, set from how its own source states the base;
#   * a ``spending`` row splits on whether it is one of CBO's own *Options*
#     alternatives (``cbo_options.runnable_score_ids()``, i.e. a budget-authority
#     path CBO published) or a Phase D enacted-law component.
#
# Display labels are §2's; the slugs are what the CLI and the workflow speak.
POLICY_CLASS_LABELS: dict[str, str] = {
    "agi_inclusive_surtax": "AGI-inclusive surtax",
    "ordinary_rate_change": "ordinary rate change",
    "capital_gains": "capital gains",
    "corporate": "corporate",
    "enacted_law_spending": "enacted-law spending",
    "discretionary_spending": "discretionary spending",
    "payroll": "payroll",
    "tax_expenditure": "tax expenditure",
}

#: Returned when a record's shape matches none of the rules above. It is never
#: silently dropped: ``--max-class-mean-error`` fails on it, because "a class
#: nobody gated" is how PR #119's four offset-sign defects got in.
UNCLASSIFIED_CLASS = "unclassified"


def classify_policy(policy_id: str) -> str:
    """Return the §2 policy-class slug for one out-of-sample ``policy_id``."""
    score = KNOWN_SCORES.get(policy_id)
    if score is None:
        return UNCLASSIFIED_CLASS

    policy_type = getattr(score.policy_type, "value", str(score.policy_type))
    if policy_type == "corporate_tax":
        return "corporate"
    if policy_type == "payroll_tax":
        return "payroll"
    if policy_type == "tax_expenditure":
        return "tax_expenditure"
    if policy_type == "capital_gains_tax":
        return "capital_gains"
    if policy_type == "income_tax":
        if getattr(score, "agi_inclusive_base", False):
            return "agi_inclusive_surtax"
        return "ordinary_rate_change"
    if policy_type == "spending":
        if policy_id in runnable_score_ids():
            return "discretionary_spending"
        return "enacted_law_spending"
    return UNCLASSIFIED_CLASS


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
            "target_retired": getattr(e, "target_retired", False),
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
    # runners (international, trade, pharma, enforcement, climate) and by the
    # Phase D P.L. 119-21 line-item runner are scored against figures their
    # modules were never fitted to, so folding them into the calibrated mean
    # would misdescribe both tiers.
    cal = [e for e in specialized if getattr(e, "calibrated_to_target", True)]
    # A row whose target the ledger has *withdrawn* is neither fitted nor a
    # reconstruction: there is no published figure it reconstructs, so its
    # error measures nothing and belongs in no tier mean. It is not deleted —
    # it gets its own block below, and ``uncalibrated_reconstruction_retired_
    # held_in_place`` reports the reconstruction tier with these rows folded
    # back at the error they carried when they were withdrawn, so a mean that
    # fell because a row left is readable as such.
    retired = [e for e in specialized if getattr(e, "target_retired", False)]
    recon = [
        e
        for e in specialized
        if not getattr(e, "calibrated_to_target", True)
        and not getattr(e, "target_retired", False)
    ]

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

    def _classes(entries) -> dict:
        """Tier 1 by ``planning/HIGH_STAKES_ACCURACY.md`` §2's eight classes.

        Reported alongside the pooled summary, never instead of it: the tier is
        eight populations and the pooled mean cannot see one of them regressing
        while the others carry it.
        """
        buckets: dict[str, list] = {}
        for entry in entries:
            buckets.setdefault(classify_policy(entry.policy_id), []).append(entry)
        out = {}
        for slug, rows in buckets.items():
            # Aggregated on each row's error **as reported** -- rounded to one
            # decimal, the figure ``entries`` above carries and the figure every
            # lane doc and CLAUDE.md quotes. Summing the unrounded errors instead
            # would put this block a tenth of a point away from the published
            # record on every class, for no gain in accuracy.
            errs = sorted(round(e.abs_percent_difference, 1) for e in rows)
            mid = len(errs) // 2
            median = errs[mid] if len(errs) % 2 else (errs[mid - 1] + errs[mid]) / 2
            out[slug] = {
                "label": POLICY_CLASS_LABELS.get(slug, slug),
                "n": len(errs),
                "mean_abs_error": round(sum(errs) / len(errs), 1),
                "median_abs_error": round(median, 1),
                "error_mass": round(sum(errs), 1),
                "within_15pct": sum(1 for e in errs if e <= 15.0),
                "within_25pct": sum(1 for e in errs if e <= 25.0),
                "policy_ids": sorted(e.policy_id for e in rows),
            }
        return out

    return {
        "out_of_sample": {
            "summary": _agg(uncal),
            "classes": _classes(uncal),
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
        # The two blocks that make a withdrawal visible. The first is what was
        # withdrawn and what error each row carried; the second is the
        # reconstruction tier with those rows put back, so "the tier improved"
        # can never be a consequence of retiring rows without the arithmetic
        # being on the same page.
        "retired_targets": {
            "summary": _agg(retired),
            "entries": [
                _entry_dict(e)
                for e in sorted(retired, key=lambda x: x.abs_percent_difference)
            ],
        },
        "uncalibrated_reconstruction_retired_held_in_place": {
            "summary": _agg(recon + retired),
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

    classes = oos.get("classes") or {}
    if classes:
        print()
        print("  By policy class (HIGH_STAKES_ACCURACY.md section 2) - the tier is")
        print("  eight populations, and the pooled mean above cannot see one of")
        print("  them regressing while the others carry it:")
        print()
        print(f"  {'Class':<24}{'n':>4}{'mean':>8}{'median':>8}{'mass':>8}{'w/in 15':>9}")
        print("  " + "-" * 60)
        for slug in sorted(classes, key=lambda k: -classes[k]["error_mass"]):
            c = classes[slug]
            print(
                f"  {c['label'][:23]:<24}{c['n']:>4}{c['mean_abs_error']:>7.1f}%"
                f"{c['median_abs_error']:>7.1f}%{c['error_mass']:>8.1f}"
                f"{str(c['within_15pct']) + '/' + str(c['n']):>9}"
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

    retired = report.get("retired_targets")
    if retired and retired["summary"]["n"]:
        rt = retired["summary"]
        recon_summary = report["uncalibrated_reconstruction"]["summary"]
        held = report["uncalibrated_reconstruction_retired_held_in_place"][
            "summary"
        ]
        print()
        print("-" * 72)
        print("RETIRED TARGETS (withdrawn: not a score of anything, no replacement)")
        print("-" * 72)
        print(
            f"  {rt['n']} row(s), carrying mean abs error {rt['mean_abs_error']}%"
            " on the day they were withdrawn."
        )
        for e in retired["entries"]:
            print(
                f"    {e['policy_id']:<34}"
                f"{e['official_10yr_billions']:>+10.0f}"
                f"{e['model_10yr_billions']:>+10.0f}"
                f"{e['abs_percent_error']:>7.0f}%"
            )
        print(
            "  These rows keep their scorecard entry and their model figure; what"
            " they no\n  longer have is a target, so their error is not in the"
            " reconstruction mean\n  above. Read the two together:"
            f" reconstructions {recon_summary['n']}"
            f" @ {recon_summary['mean_abs_error']}%"
            f" vs {held['n']} @ {held['mean_abs_error']}%\n  with the retired rows"
            " held in place. A tier that improved because a row was\n  withdrawn"
            " is not a tier that improved."
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
    parser.add_argument(
        "--max-class-mean-error",
        nargs="+",
        metavar="CLASS=PERCENT",
        default=None,
        help="Per-class ceilings, as SLUG=PERCENT pairs over the eight policy "
        "classes of planning/HIGH_STAKES_ACCURACY.md section 2 (CI guardrail). The "
        "pooled mean cannot see one class regressing while the others carry "
        "it. Every class the battery contains must be given a ceiling and "
        "every ceiling must name a class that exists, so a newly-registered "
        "row cannot escape the gate by landing in a class nobody listed. "
        "Slugs: " + ", ".join(sorted(POLICY_CLASS_LABELS)) + ".",
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

    if args.max_class_mean_error is not None:
        if _check_class_ceilings(
            report["out_of_sample"].get("classes", {}), args.max_class_mean_error
        ):
            failed = True

    return 1 if failed else 0


def _check_class_ceilings(classes: dict, pairs: list[str]) -> bool:
    """Apply ``--max-class-mean-error``. Returns True if the gate failed.

    Three ways to fail, and the last two matter as much as the first: a class
    over its ceiling; a class in the battery that was given **no** ceiling; and
    a ceiling naming a class that does not exist. A gate that silently ignores
    an unlisted class is the failure mode PR #119's coverage-grep test exists
    to prevent -- a new pre-registered row in a ninth class would sail past it.
    """
    ceilings: dict[str, float] = {}
    failed = False
    for pair in pairs:
        slug, _, raw = pair.partition("=")
        slug = slug.strip()
        if not _:
            print(
                f"\nFAIL: --max-class-mean-error expects SLUG=PERCENT, got {pair!r}",
                file=sys.stderr,
            )
            return True
        try:
            ceilings[slug] = float(raw)
        except ValueError:
            print(
                f"\nFAIL: --max-class-mean-error ceiling for {slug!r} is not a "
                f"number: {raw!r}",
                file=sys.stderr,
            )
            return True

    unknown = sorted(set(ceilings) - set(POLICY_CLASS_LABELS))
    if unknown:
        print(
            f"\nFAIL: --max-class-mean-error names class(es) that do not exist: "
            f"{', '.join(unknown)}. Known slugs: "
            f"{', '.join(sorted(POLICY_CLASS_LABELS))}",
            file=sys.stderr,
        )
        failed = True

    ungated = sorted(set(classes) - set(ceilings))
    if ungated:
        print(
            "\nFAIL: out-of-sample class(es) with no ceiling: "
            f"{', '.join(ungated)}. Every class the battery contains must be "
            "gated, or a newly-registered row lands in an ungated class and the "
            "per-class floor stops meaning anything.",
            file=sys.stderr,
        )
        failed = True

    for slug in sorted(classes):
        if slug not in ceilings:
            continue
        mean_err = classes[slug]["mean_abs_error"]
        if mean_err > ceilings[slug]:
            print(
                f"\nFAIL: class {classes[slug]['label']!r} mean abs error "
                f"{mean_err}% over {classes[slug]['n']} case(s) exceeds its "
                f"ceiling {ceilings[slug]}%",
                file=sys.stderr,
            )
            failed = True

    return failed


if __name__ == "__main__":
    raise SystemExit(main())
