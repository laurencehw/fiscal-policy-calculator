#!/usr/bin/env python3
"""
Decompose the corporate module's implied marginal share, and print the four
things lane R5 examined on the way to it.

``scripts/corporate_yield_reconciliation.py`` answers "what share of the average
base does each *published* estimator reach?" (55.1% Tax Foundation, 55.9% JCT,
64.4% PWBM, 79.5% Treasury OTA). This script answers the other half: **what does
this model's own share consist of**, and which of the candidate mechanisms for
closing the gap survive contact with a source.

Nothing here scores a benchmark or moves a target. Every table is arithmetic on
the module's own published inputs, kept in a script so that
``planning/lanes/R5_h3b_corporate.md`` can be re-derived rather than believed.

The sections map one-to-one onto that lane's §1:

1. **The factor decomposition.** The derived path's total factor against the
   vintage's average base, split into the base conversion, the behavioural term
   and the IRC §6655 phase. Printed beside the two numbers a lane may not
   approach by assertion: **0.5785**, the total factor that reproduces CBO
   Option 64, and JCT's own steady-state **0.590**.
2. **CBO's loss-firm haircut, and why it is not applied.** The three readings in
   ``fiscal_model/data_files/corporate/cbo_loss_firm_haircut.csv``, with the one
   that is a measurement computed rather than quoted.
2b. **Credit carryforwards.** The §38(c) and §904(c) stocks the memo called a
   data-acquisition item, now acquired
   (``credit_carryforward_stocks.csv``), bounded, and not priced — because the
   share of the base in the constrained position is unpublished after TY2010.
3. **The entity-choice leg.** ``_estimate_passthrough_shift`` at every step the
   repository scores.
4. **The direction asymmetry.** Tax Foundation *Options 2.0* prices a cut 29%
   dearer per point than an increase; what each mode produces.

Usage
-----
    python scripts/corporate_marginal_share.py
    python scripts/corporate_marginal_share.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.corporate import (  # noqa: E402
    BASE_PER_DOLLAR_OF_RECEIPTS,
    CBO_BUSINESS_INVESTMENT_MODEL_COMMIT,
    CORPORATE_MODE_DERIVED,
    CORPORATE_MODE_REPORTED,
    CURRENT_CORPORATE_RATE,
    PROFIT_SHIFTING_SEMI_ELASTICITY,
    CorporateTaxPolicy,
    cbo_corporate_receipts,
    cbo_loss_firm_haircut,
    credit_absorption_bounds,
    credit_realization_ratio,
    load_cbo_loss_firm_haircut,
    load_soi_table11,
    loss_firm_haircut_is_redundant,
    soi_row,
)
from fiscal_model.policies import PolicyType  # noqa: E402

#: The two numbers ``planning/memos/CORPORATE_PER_POINT_YIELD.md`` §6 names and
#: forbids arriving at by assertion. Printed so that a reader can see how far a
#: change moved the model *toward* them without any lane having aimed at them.
OPTION_64_REPRODUCING_FACTOR = 0.5785
JCT_STEADY_STATE_SHARE = 0.590

#: Tax Foundation, *Options for Reforming America's Tax Code 2.0* (2021):
#: Option 36 raises 21% -> 28% for $886.3B ($126.6B/pt); Option 11 cuts
#: 21% -> 15% for $978.9B ($163.2B/pt). The only edition pricing both directions
#: in one model, one window.
TAX_FOUNDATION_OPTIONS_2_INCREASE_PER_POINT = 126.6
TAX_FOUNDATION_OPTIONS_2_CUT_PER_POINT = 163.2

WINDOW = tuple(range(2025, 2035))


def _policy(rate_change: float, mode: str) -> CorporateTaxPolicy:
    return CorporateTaxPolicy(
        name=f"{rate_change:+.2%} corporate rate",
        description="rate change only",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=rate_change,
        mode=mode,
        start_year=WINDOW[0],
        duration_years=len(WINDOW),
    )


def factor_decomposition(rate_change: float = 0.01) -> dict:
    """The derived path's total factor against the vintage's average base."""
    policy = _policy(rate_change, CORPORATE_MODE_DERIVED)
    new_rate = CURRENT_CORPORATE_RATE + rate_change

    years = []
    net_total = avg_base_total = 0.0
    for year in WINDOW:
        average_base = cbo_corporate_receipts(year) / CURRENT_CORPORATE_RATE
        static = policy.estimate_static_revenue_effect(0.0, True, year)
        offset = policy.estimate_behavioral_offset(static)
        phase = policy.get_phase_in_factor(year)
        net = (static - offset) * phase
        years.append(
            {
                "fiscal_year": year,
                "average_base_billions": average_base,
                "static_billions": static,
                "behavioural_offset_billions": offset,
                "phase_factor": phase,
                "net_billions": net,
                "marginal_share": (net / rate_change) / average_base,
            }
        )
        net_total += net
        avg_base_total += average_base

    window_share = (net_total / rate_change) / avg_base_total
    return {
        "rate_change_pp": rate_change * 100.0,
        "factors": {
            "base_conversion_vs_one_over_tau": BASE_PER_DOLLAR_OF_RECEIPTS
            * CURRENT_CORPORATE_RATE,
            "behavioural_1_minus_beta_tau": 1.0
            - PROFIT_SHIFTING_SEMI_ELASTICITY * new_rate,
            "profit_shifting_semi_elasticity": PROFIT_SHIFTING_SEMI_ELASTICITY,
            "credit_realization_ratio_inside_the_anchor": credit_realization_ratio(),
        },
        "window_marginal_share": window_share,
        "ten_year_total_billions": net_total,
        "forbidden_targets": {
            "option_64_reproducing_total_factor": OPTION_64_REPRODUCING_FACTOR,
            "jct_steady_state_share": JCT_STEADY_STATE_SHARE,
            "distance_to_option_64_factor": window_share
            - OPTION_64_REPRODUCING_FACTOR,
            "distance_to_jct_share": window_share - JCT_STEADY_STATE_SHARE,
        },
        "years": years,
    }


def loss_firm_haircut_report() -> dict:
    """CBO's 0.80/0.85, and the measurement that says not to apply it here."""
    rows = {r["variable"]: r for r in load_cbo_loss_firm_haircut()}
    by_year = {}
    for row in load_soi_table11():
        year = int(row["tax_year"])
        by_year[year] = loss_firm_haircut_is_redundant(year)

    anchor = max(by_year)
    shares = [v["soi_nol_share_of_pre_nol_base"] for v in by_year.values()]
    would_be = {}
    for name in ("dmyrevnfc", "dmyrevx"):
        factor = cbo_loss_firm_haircut(name)
        would_be[name] = {
            "factor": factor,
            "derived_1pp_total_billions": factor
            * factor_decomposition(0.01)["ten_year_total_billions"],
        }

    return {
        "source": {
            "repository": "github.com/US-CBO/business-investment-model",
            "commit": CBO_BUSINESS_INVESTMENT_MODEL_COMMIT,
            "constants": {k: float(v["factor"]) for k, v in rows.items()},
            "lines": {k: v["source_line"] for k, v in rows.items()},
            "scopes": {k: v["scope"] for k, v in rows.items()},
            "is_financial_vs_nonfinancial": False,
            "note": (
                "0.85 is loss firms alone (nonfinancial corporates); 0.80 is that "
                "same factor further reduced by the nonprofit share of private "
                "nonresidential investment. There is no financial-sector series."
            ),
        },
        "applies_to": "a statutory RATE in a user-cost expression, not a base",
        "measurement": {
            "per_tax_year": by_year,
            "anchor_year": anchor,
            "soi_nol_share_mean": sum(shares) / len(shares),
            "cbo_loss_share": by_year[anchor]["cbo_loss_share_of_positive_net_income"],
            "gap_pp_at_anchor": by_year[anchor]["gap_pp"],
        },
        "verdict": "redundant with the derived base; not applied",
        "counterfactual": would_be,
    }


def entity_choice_leg() -> dict:
    """``_estimate_passthrough_shift`` at every step the repository scores."""
    steps = {"cbo_opt64 +1pp": 0.01, "biden +7pp": 0.07, "trump -6pp": -0.06}
    out = {}
    for label, step in steps.items():
        policy = _policy(step, CORPORATE_MODE_DERIVED)
        out[label] = {
            "new_corporate_rate": CURRENT_CORPORATE_RATE + step,
            "individual_effective_rate_hardcoded": 0.296,
            "shift_billions": policy._estimate_passthrough_shift(),
        }
    out["finding"] = (
        "Returns exactly 0.0 at every step the repository scores, and for every "
        "rate cut by construction: the leg fires only when the corporate rate "
        "exceeds a hard-coded 29.6% individual effective rate, which 22%, 28% "
        "and 15% do not. JCT names entity choice as one of its five corporate "
        "behavioural margins (JCX-46-11 p. 10) and publishes no parameter for "
        "it, so this lane measures the leg rather than replacing it."
    )
    return out


def direction_asymmetry() -> dict:
    """A point of cut versus a point of increase, model against Tax Foundation."""
    published = {
        "tax_foundation_options_2_increase_per_point_billions": (
            TAX_FOUNDATION_OPTIONS_2_INCREASE_PER_POINT
        ),
        "tax_foundation_options_2_cut_per_point_billions": (
            TAX_FOUNDATION_OPTIONS_2_CUT_PER_POINT
        ),
        "published_asymmetry": TAX_FOUNDATION_OPTIONS_2_CUT_PER_POINT
        / TAX_FOUNDATION_OPTIONS_2_INCREASE_PER_POINT
        - 1.0,
    }
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        per_point = {}
        for label, step in (("increase_7pp", 0.07), ("cut_6pp", -0.06)):
            policy = _policy(step, mode)
            total = 0.0
            for year in WINDOW:
                static = policy.estimate_static_revenue_effect(0.0, True, year)
                offset = policy.estimate_behavioral_offset(static)
                total += (static - offset) * policy.get_phase_in_factor(year)
            per_point[label] = abs(total / (step * 100.0))
        per_point["asymmetry"] = per_point["cut_6pp"] / per_point["increase_7pp"] - 1.0
        published[mode] = per_point
    return published


def _fmt(report: dict) -> str:
    lines: list[str] = []
    dec = report["decomposition"]
    lines.append("=" * 74)
    lines.append("1. The derived path's marginal share, decomposed")
    lines.append("=" * 74)
    f = dec["factors"]
    lines.append(
        f"  base conversion (BASE_PER_DOLLAR_OF_RECEIPTS x tau):  {f['base_conversion_vs_one_over_tau']:.4f}"
    )
    lines.append(
        f"  behavioural (1 - beta x tau_1), beta={f['profit_shifting_semi_elasticity']}:        "
        f"{f['behavioural_1_minus_beta_tau']:.4f}"
    )
    lines.append(
        f"  window marginal share at +1pp:                        {dec['window_marginal_share']:.4f}"
    )
    ft = dec["forbidden_targets"]
    lines.append("")
    lines.append("  Named and not aimed at (CORPORATE_PER_POINT_YIELD.md §6):")
    lines.append(
        f"    total factor reproducing CBO Option 64:  {ft['option_64_reproducing_total_factor']:.4f}"
        f"   (distance {ft['distance_to_option_64_factor']:+.4f})"
    )
    lines.append(
        f"    JCT's own steady-state share:            {ft['jct_steady_state_share']:.4f}"
        f"   (distance {ft['distance_to_jct_share']:+.4f})"
    )
    lines.append("")
    lines.append("    FY   avg base $B   net $B    share")
    for row in dec["years"]:
        lines.append(
            f"  {row['fiscal_year']}   {row['average_base_billions']:10,.1f}"
            f"  {row['net_billions']:8.2f}   {row['marginal_share']:.4f}"
        )

    haircut = report["loss_firm_haircut"]
    lines.append("")
    lines.append("=" * 74)
    lines.append("2. CBO's loss-firm haircut: read, measured, not applied")
    lines.append("=" * 74)
    src = haircut["source"]
    lines.append(f"  {src['repository']} @ {src['commit'][:12]}")
    for name, value in src["constants"].items():
        lines.append(f"    {name} = {value}   ({src['scopes'][name]}) {src['lines'][name]}")
    lines.append(f"  applies to: {haircut['applies_to']}")
    lines.append("")
    m = haircut["measurement"]
    lines.append("  Is it already in the base? SOI's own NOL deduction says yes:")
    lines.append("    TY    income subject to tax    NOL ded.    NOL / (base + NOL)")
    for year, vals in sorted(m["per_tax_year"].items()):
        row = soi_row(year)
        base = float(row["income_subject_to_tax_thousands"]) / 1e6
        nol = float(row["net_operating_loss_deduction_thousands"]) / 1e6
        lines.append(
            f"    {year}   {base:18,.1f}   {nol:9,.1f}    "
            f"{vals['soi_nol_share_of_pre_nol_base']:.4f}"
        )
    lines.append(
        f"    CBO's own loss share (SOI 2005 flow):            {m['cbo_loss_share']:.4f}"
    )
    lines.append(
        f"    gap at the anchor year TY{m['anchor_year']}:"
        f"                  {m['gap_pp_at_anchor']:.2f} pp"
    )
    lines.append(f"  VERDICT: {haircut['verdict']}")
    lines.append("")
    lines.append("  What applying it anyway would have returned at +1pp:")
    for _name, vals in haircut["counterfactual"].items():
        lines.append(
            f"    x{vals['factor']}  ->  {vals['derived_1pp_total_billions']:,.2f} $B"
        )

    cab = report["credit_absorption"]
    lines.append("")
    lines.append("=" * 74)
    lines.append("2b. Credit carryforwards: the stocks exist, the shares do not")
    lines.append("=" * 74)
    lines.append(
        f"  average substitution the derived path already books:  "
        f"{cab['average_substitution_in_use']:.4f}"
    )
    lines.append(
        f"  section 904 upper bound (every claimant excess-credit): "
        f"{cab['section_904_upper_bound']:.4f}"
    )
    lines.append(
        f"    unclaimed foreign taxes, TY2022:                     "
        f"${cab['section_904_unclaimed_foreign_taxes_billions']:,.1f}B"
    )
    lines.append(
        f"  section 38(c) upper bound (statutory cap on the margin): "
        f"{cab['section_38c_upper_bound']:.4f}"
    )
    lines.append(
        f"    carryforward stock into TY2022:                      "
        f"${cab['section_38c_carryforward_stock_billions']:,.1f}B"
        f"  ({cab['section_38c_stock_in_years_of_claims']:.2f} years of claims)"
    )
    lines.append(
        "  READING: the average substitution sits within "
        f"{abs(cab['average_substitution_in_use'] - cab['section_904_upper_bound']) * 100:.2f}"
        " pp of the section 904 bound, so the section 38(c) channel is unbooked."
        " Its realized size needs the share of the base held by taxpayers both"
        " capped and holding stock, which is unpublished for every post-TCJA"
        " year (SOI's excess-position tables stop at TY2010)."
    )

    entity = report["entity_choice"]
    lines.append("")
    lines.append("=" * 74)
    lines.append("3. The entity-choice leg")
    lines.append("=" * 74)
    for label, vals in entity.items():
        if label == "finding":
            continue
        lines.append(
            f"  {label:16s} new rate {vals['new_corporate_rate']:.2%}  "
            f"shift = {vals['shift_billions']:.2f} $B"
        )
    lines.append(f"  {entity['finding']}")

    asym = report["direction_asymmetry"]
    lines.append("")
    lines.append("=" * 74)
    lines.append("4. A point of cut versus a point of increase")
    lines.append("=" * 74)
    lines.append(
        f"  Tax Foundation Options 2.0: increase "
        f"${asym['tax_foundation_options_2_increase_per_point_billions']:.1f}/pt, "
        f"cut ${asym['tax_foundation_options_2_cut_per_point_billions']:.1f}/pt "
        f"-> {asym['published_asymmetry']:+.1%}"
    )
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        vals = asym[mode]
        lines.append(
            f"  model {mode:9s}: increase ${vals['increase_7pp']:.2f}/pt, "
            f"cut ${vals['cut_6pp']:.2f}/pt -> {vals['asymmetry']:+.1%}"
        )
    return "\n".join(lines)


def build_report() -> dict:
    return {
        "decomposition": factor_decomposition(0.01),
        "loss_firm_haircut": loss_firm_haircut_report(),
        "credit_absorption": credit_absorption_bounds(),
        "entity_choice": entity_choice_leg(),
        "direction_asymmetry": direction_asymmetry(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, default=float))
    else:
        print(_fmt(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
