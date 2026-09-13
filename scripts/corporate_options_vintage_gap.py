#!/usr/bin/env python3
"""
Decompose the four CBO *Options* corporate +1pp rows by receipts vintage.

CHECK-ONLY. Nothing here scores a new target, retunes a constant, or writes a
file. It is the arithmetic behind ``planning/lanes/CORP_class_accuracy.md`` and
the outturn of ``planning/lanes/CORP_outlook_vintages.md``, kept in a script so
those tables can be re-derived rather than believed.

**The install has happened.** Each of the four rows now names the CBO Outlook
its own *Options* volume was priced against
(``CBOScore.corporate_receipts_vintage``), and
``data_files/corporate/cbo_corporate_receipts.csv`` carries a block for each.
So the ``contemporaneous_*`` figures this script used to print as a *prediction*
are the **live** scores, and it is the ``contemporaneous`` reconstruction that
now matches them to the dollar.

Three columns, and they are three different quantities:

``live`` / ``contemporaneous``
    The score, and this script's reconstruction of it on that edition's own
    Outlook path. They agree to $0.000B, which is what makes the arithmetic
    below checkable rather than believed.
``pre_install``
    **History.** What each row scored when every window read the February 2024
    block, back-extrapolated at its own leading growth rate into years it does
    not cover — 99.7% / 93.1% / 49.2% / 44.5%. Kept so the install's size stays
    on the record and so nobody re-derives it by guessing.
``first_year_mts``
    R3's **diagnostic**, and not the install. Deflating a ten-year score by its
    first fiscal year's projected-over-actual receipts ratio gives 10.0% and
    42.2% on the two oldest rows. It over-deflates a window whose later years
    are already on the February 2024 block, and it deflates toward *actuals*
    where JCT scored a *projection*. Kept printed so it cannot be quoted as the
    install's outturn.

Usage
-----
    python scripts/corporate_options_vintage_gap.py
    python scripts/corporate_options_vintage_gap.py --json
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
    CURRENT_CORPORATE_RATE,
    ESTIMATED_PAYMENT_SAME_FY_SHARE,
    PROFIT_SHIFTING_SEMI_ELASTICITY,
    actual_corporate_receipts,
    cbo_corporate_receipts,
    corporate_receipts_document,
    corporate_receipts_sourcing,
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES  # noqa: E402
from fiscal_model.validation.core import validate_policy  # noqa: E402

POLICY_IDS = (
    "cbo2019_opt24_corporate_rate_1pp",
    "cbo2021_opt19_corporate_rate_1pp",
    "cbo2023_opt50_corporate_rate_1pp",
    "cbo_opt64_corporate_rate_1pp",
)

#: Each Options row names the Outlook its volume was priced on — and since
#: ``CORP_outlook_vintages.md`` the *record itself* names it, so this map is
#: read off ``KNOWN_SCORES`` rather than kept by hand. A row that stops naming
#: one raises here rather than silently reverting to the February 2024 block,
#: which is the failure this script exists to make visible.
CONTEMPORANEOUS_VINTAGE = {
    policy_id: KNOWN_SCORES[policy_id].corporate_receipts_vintage
    for policy_id in POLICY_IDS
}

_UNNAMED = [pid for pid, vintage in CONTEMPORANEOUS_VINTAGE.items() if not vintage]
if _UNNAMED:
    raise SystemExit(
        "These corporate rows name no receipts vintage, so they are scored on "
        f"the module default rather than their own Outlook: {_UNNAMED}"
    )

#: What every window read before ``CORP_outlook_vintages.md`` wired the three
#: older Outlooks: the February 2024 block, back-extrapolated at its own
#: leading growth rate into years it does not cover.
PRE_INSTALL_VINTAGE = "cbo_feb_2024"

RATE_STEP = 0.01
NEW_RATE = CURRENT_CORPORATE_RATE + RATE_STEP
OFFSET_SHARE = PROFIT_SHIFTING_SEMI_ELASTICITY * NEW_RATE  # 0.8 × 0.22


def _window(policy_id: str) -> tuple[int, ...]:
    score = KNOWN_SCORES[policy_id]
    start = int(score.scoring_window_first_year or score.effective_start_year)
    return tuple(range(start, start + 10))


def _contemporaneous_path(policy_id: str) -> dict[int, float]:
    """That edition's own Outlook path, from the file the engine reads.

    Not from ``corporate_yield_reconciliation.BASELINES``: since the install,
    the four scored blocks live in
    ``data_files/corporate/cbo_corporate_receipts.csv`` and ``BASELINES`` fills
    its own annuals from there. Reading the data file directly is what makes
    the reconstruction below a check on the engine rather than a check on a
    copy of the engine's input.
    """
    from fiscal_model.corporate import cbo_receipts_by_fiscal_year

    key = CONTEMPORANEOUS_VINTAGE[policy_id]
    return dict(cbo_receipts_by_fiscal_year(key))


def _phase_factor(year: int, start_year: int, receipts_at) -> float:
    if year <= start_year:
        return ESTIMATED_PAYMENT_SAME_FY_SHARE
    prior = receipts_at(year - 1)
    current = receipts_at(year)
    return ESTIMATED_PAYMENT_SAME_FY_SHARE + (
        1.0 - ESTIMATED_PAYMENT_SAME_FY_SHARE
    ) * (prior / current)


def _pre_install_receipts(fiscal_year: int) -> float:
    """The February-2024-only path every row read before the install."""
    return cbo_corporate_receipts(fiscal_year, PRE_INSTALL_VINTAGE)


def _score_on_path(window: tuple[int, ...], receipts_at) -> dict:
    """Reproduce the derived +1pp identity on an arbitrary receipts path."""
    start = window[0]
    years = []
    net_total = 0.0
    receipts_total = 0.0
    for year in window:
        receipts = receipts_at(year)
        static = RATE_STEP * receipts * BASE_PER_DOLLAR_OF_RECEIPTS
        phase = _phase_factor(year, start, receipts_at)
        net = static * phase * (1.0 - OFFSET_SHARE)
        net_total += net
        receipts_total += receipts
        years.append(
            {
                "fiscal_year": year,
                "receipts_billions": receipts,
                "static_billions": static,
                "phase_factor": phase,
                "net_billions": net,
            }
        )
    return {
        "model_10yr_billions": -net_total,
        "receipts_billions_total": receipts_total,
        "years": years,
    }


def _live_row(policy_id: str) -> dict:
    result = validate_policy(KNOWN_SCORES[policy_id], dynamic=False)
    if result is None:
        raise RuntimeError(f"{policy_id} did not score")
    return {
        "policy_id": policy_id,
        "target_10yr_billions": result.official_10yr,
        "model_10yr_billions": result.model_10yr,
        "error_pct": result.abs_percent_difference,
    }


def _mts_or_none(year: int) -> float | None:
    try:
        return actual_corporate_receipts(year)
    except KeyError:
        return None


def _row_report(policy_id: str) -> dict:
    live = _live_row(policy_id)
    window = _window(policy_id)
    contemporaneous = _contemporaneous_path(policy_id)
    pre_install = _score_on_path(window, _pre_install_receipts)
    vintage = _score_on_path(window, contemporaneous.__getitem__)

    first_year = window[0]
    shipped_first = _pre_install_receipts(first_year)
    mts_first = _mts_or_none(first_year)
    first_year_ratio = (
        shipped_first / mts_first if mts_first and mts_first != 0 else None
    )
    # R3's diagnostic, reproduced on the quantity R3 computed it on: the
    # PRE-INSTALL model figure, not the live one. Deflating the live score by a
    # first-year ratio would be a third quantity nobody published, and the whole
    # reason this column is kept is so 10.0% / 42.2% / 25.3% stay reproducible
    # and stay visibly NOT the install.
    first_year_deflated = (
        pre_install["model_10yr_billions"] / first_year_ratio
        if first_year_ratio
        else None
    )

    mts_pairs = []
    for year in window:
        actual = _mts_or_none(year)
        if actual is None:
            continue
        mts_pairs.append((_pre_install_receipts(year), actual))
    window_mean_ratio = (
        (sum(p[0] for p in mts_pairs) / sum(p[1] for p in mts_pairs))
        if mts_pairs
        else None
    )

    target = live["target_10yr_billions"]

    def _err(model: float) -> float:
        return abs(model - target) / abs(target) * 100.0

    # The reconstruction that must match the LIVE score is now the one on each
    # edition's own Outlook path, because that is what the engine reads.
    reconstruction_gap = abs(
        vintage["model_10yr_billions"] - live["model_10yr_billions"]
    )

    return {
        **live,
        "window": f"FY{window[0]}-{window[-1]}",
        "contemporaneous_vintage": CONTEMPORANEOUS_VINTAGE[policy_id],
        "contemporaneous_document": corporate_receipts_document(
            CONTEMPORANEOUS_VINTAGE[policy_id]
        ),
        "contemporaneous_sourcing": corporate_receipts_sourcing(
            CONTEMPORANEOUS_VINTAGE[policy_id]
        ),
        "reconstruction_10yr": vintage["model_10yr_billions"],
        "reconstruction_gap": reconstruction_gap,
        "pre_install_model_10yr": pre_install["model_10yr_billions"],
        "pre_install_error_pct": _err(pre_install["model_10yr_billions"]),
        "pre_install_receipts_10yr": pre_install["receipts_billions_total"],
        "contemporaneous_model_10yr": vintage["model_10yr_billions"],
        "contemporaneous_error_pct": _err(vintage["model_10yr_billions"]),
        "contemporaneous_receipts_10yr": vintage["receipts_billions_total"],
        "receipts_ratio_pre_install_over_contemporaneous": (
            pre_install["receipts_billions_total"]
            / vintage["receipts_billions_total"]
        ),
        "first_year_shipped_receipts": shipped_first,
        "first_year_mts_receipts": mts_first,
        "first_year_mts_ratio": first_year_ratio,
        "first_year_mts_deflated_model": first_year_deflated,
        "first_year_mts_deflated_error_pct": (
            _err(first_year_deflated) if first_year_deflated is not None else None
        ),
        "mts_years_in_window": len(mts_pairs),
        "window_mean_mts_ratio": window_mean_ratio,
        "years": [
            {
                "fiscal_year": year,
                "pre_install_receipts": _pre_install_receipts(year),
                "contemporaneous_receipts": contemporaneous[year],
                "mts_receipts": _mts_or_none(year),
                "on_transcribed_feb_2024_block": year >= 2025,
            }
            for year in window
        ],
    }


def build_report() -> dict:
    rows = [_row_report(policy_id) for policy_id in POLICY_IDS]
    live_mass = sum(row["error_pct"] for row in rows)
    pre_install_mass = sum(row["pre_install_error_pct"] for row in rows)
    return {
        "rows": rows,
        "n": len(rows),
        "live_class_mean_pct": live_mass / len(rows),
        "live_error_mass": live_mass,
        # Retained keys: the live column IS the contemporaneous one since the
        # install, and a reader comparing this report with the lane docs that
        # predicted it should not have to translate names to see that.
        "contemporaneous_class_mean_pct": live_mass / len(rows),
        "contemporaneous_error_mass": live_mass,
        "pre_install_class_mean_pct": pre_install_mass / len(rows),
        "pre_install_error_mass": pre_install_mass,
        "mass_reduction": pre_install_mass - live_mass,
        "offset_share": OFFSET_SHARE,
        "base_per_dollar_of_receipts": BASE_PER_DOLLAR_OF_RECEIPTS,
        "reconstruction_tolerance_billions": 0.15,
    }


def _fmt(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def render(report: dict) -> str:
    lines = [
        "Corporate +1pp Options rows — each on the Outlook its own volume names",
        "",
        f"Derived identity: Δτ × receipts × {report['base_per_dollar_of_receipts']:.5f} "
        f"× (1 − {report['offset_share']:.3f}) × §6655 phase.",
        "LIVE: each row reads the block CBOScore.corporate_receipts_vintage "
        "names, from cbo_corporate_receipts.csv.",
        "PRE-INSTALL (history): what every row scored when all four windows "
        "read the February 2024 block,",
        "  back-extrapolated at its own leading growth rate before FY2025.",
        "",
        f"{'row':<36} {'win':<12} {'vintage':<13} {'target':>8} {'live':>8} "
        f"{'err':>6} {'pre-inst':>9} {'err':>6} {'1yr MTS':>8} {'err':>6}",
    ]
    for row in report["rows"]:
        lines.append(
            f"{row['policy_id']:<36} {row['window']:<12} "
            f"{row['contemporaneous_vintage']:<13} "
            f"{row['target_10yr_billions']:8.1f} "
            f"{row['model_10yr_billions']:8.1f} "
            f"{row['error_pct']:5.1f}% "
            f"{row['pre_install_model_10yr']:9.1f} "
            f"{row['pre_install_error_pct']:5.1f}% "
            f"{_fmt(row['first_year_mts_deflated_model']):>8} "
            f"{_fmt(row['first_year_mts_deflated_error_pct'], 1):>5}%"
        )
    lines += [
        "",
        f"class mean  live {report['live_class_mean_pct']:.1f}%   "
        f"pre-install {report['pre_install_class_mean_pct']:.1f}%",
        f"error mass  live {report['live_error_mass']:.1f}   "
        f"pre-install {report['pre_install_error_mass']:.1f}   "
        f"the install was worth {report['mass_reduction']:.1f}",
        "",
        "Receipts 10-year totals (pre-install vs the row's own Outlook) and "
        "first-year MTS",
        f"{'row':<36} {'pre-inst $B':>12} {'own $B':>11} {'ratio':>7} "
        f"{'FY1 pre':>9} {'FY1 MTS':>8} {'FY1 ×':>6}",
    ]
    for row in report["rows"]:
        lines.append(
            f"{row['policy_id']:<36} "
            f"{row['pre_install_receipts_10yr']:12.1f} "
            f"{row['contemporaneous_receipts_10yr']:11.1f} "
            f"{row['receipts_ratio_pre_install_over_contemporaneous']:7.3f} "
            f"{row['first_year_shipped_receipts']:9.1f} "
            f"{_fmt(row['first_year_mts_receipts']):>8} "
            f"{_fmt(row['first_year_mts_ratio'], 3):>6}"
        )
    lines += [
        "",
        "First-year MTS deflation is R3's diagnostic and was never the install. "
        "It over-deflates a window whose later years are already on the",
        "February 2024 block (the 2018 row), and it deflates toward ACTUALS "
        "where JCT scored a PROJECTION. It is printed so it cannot be quoted",
        "as this install's outturn — 10.0% and 42.2% are not what the rows "
        "read.",
        "Quote the 2020 row with its clause or not at all: CBO's September 2020 "
        "Outlook projects FY2021 corporate receipts at $122.8B against a",
        "Treasury actual of $371.8B, so that row measures the module's usual "
        "marginal-share level against a COVID-depressed denominator.",
    ]
    worst_gap = max(row["reconstruction_gap"] for row in report["rows"])
    lines.append(
        f"Own-Outlook identity reconstruction matches the live scores to "
        f"${worst_gap:.3f}B (tolerance "
        f"${report['reconstruction_tolerance_billions']:.2f}B)."
    )
    grades = sorted({row["contemporaneous_sourcing"] for row in report["rows"]})
    lines.append(f"All four blocks graded: {', '.join(grades)}.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
