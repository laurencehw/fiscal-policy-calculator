#!/usr/bin/env python3
"""
Decompose the four CBO *Options* corporate +1pp rows by receipts vintage.

CHECK-ONLY. Nothing here scores a new target, retunes a constant, or writes a
file. It is the arithmetic behind ``planning/lanes/CORP_class_accuracy.md``,
kept in a script so those tables can be re-derived rather than believed.

Why this exists
---------------
Lane R3 registered four editions of one reform (21% → 22%) and found the model
answers them with a 2.2% spread where CBO/JCT's own figures span 41.0%. Its
carry-over 6 said the 2018 and 2020 blow-ups (99.7%, 93.1%) were mostly
``cbo_corporate_receipts`` walking the February 2024 path *backwards* into
years that path does not cover, and that deflating each row by its *first-year*
Treasury MTS ratio would leave 10.0% and 42.2%.

That first-year deflation is a diagnostic, not a score, and it over-deflates
the 2018 window: FY2025–2028 of that window *are* on the transcribed path.
The contemporaneous CBO Outlook paths — already transcribed as annuals in
``scripts/corporate_yield_reconciliation.py``'s ``BASELINES``, never wired
into ``cbo_corporate_receipts.csv`` — are the quantity a lane would actually
install. This script prints both readings side by side.

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
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES  # noqa: E402
from fiscal_model.validation.core import validate_policy  # noqa: E402
from scripts.corporate_yield_reconciliation import BASELINES  # noqa: E402

POLICY_IDS = (
    "cbo2019_opt24_corporate_rate_1pp",
    "cbo2021_opt19_corporate_rate_1pp",
    "cbo2023_opt50_corporate_rate_1pp",
    "cbo_opt64_corporate_rate_1pp",
)

#: Each Options row names the Outlook its volume was priced on. The keys match
#: ``BASELINES`` in the yield-reconciliation script; the annuals there are
#: CBO's own Table 1-1 (or Table 4-1 / Table 1) corporate-receipts path.
CONTEMPORANEOUS_VINTAGE = {
    "cbo2019_opt24_corporate_rate_1pp": "cbo_apr_2018",
    "cbo2021_opt19_corporate_rate_1pp": "cbo_sep_2020",
    "cbo2023_opt50_corporate_rate_1pp": "cbo_may_2022",
    "cbo_opt64_corporate_rate_1pp": "cbo_feb_2024",
}

RATE_STEP = 0.01
NEW_RATE = CURRENT_CORPORATE_RATE + RATE_STEP
OFFSET_SHARE = PROFIT_SHIFTING_SEMI_ELASTICITY * NEW_RATE  # 0.8 × 0.22


def _window(policy_id: str) -> tuple[int, ...]:
    score = KNOWN_SCORES[policy_id]
    start = int(score.scoring_window_first_year or score.effective_start_year)
    return tuple(range(start, start + 10))


def _contemporaneous_path(policy_id: str) -> dict[int, float]:
    key = CONTEMPORANEOUS_VINTAGE[policy_id]
    block = BASELINES[key]
    if not block.get("annual"):
        raise KeyError(f"{key} has no annual path transcribed")
    start = int(block["start_year"])
    return {start + i: float(value) for i, value in enumerate(block["annual"])}


def _phase_factor(year: int, start_year: int, receipts_at) -> float:
    if year <= start_year:
        return ESTIMATED_PAYMENT_SAME_FY_SHARE
    prior = receipts_at(year - 1)
    current = receipts_at(year)
    return ESTIMATED_PAYMENT_SAME_FY_SHARE + (
        1.0 - ESTIMATED_PAYMENT_SAME_FY_SHARE
    ) * (prior / current)


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
        "receipts_10yr_billions": receipts_total,
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
    shipped = _score_on_path(window, cbo_corporate_receipts)
    vintage = _score_on_path(window, contemporaneous.__getitem__)

    first_year = window[0]
    shipped_first = cbo_corporate_receipts(first_year)
    mts_first = _mts_or_none(first_year)
    first_year_ratio = (
        shipped_first / mts_first if mts_first and mts_first != 0 else None
    )
    first_year_deflated = (
        live["model_10yr_billions"] / first_year_ratio
        if first_year_ratio
        else None
    )

    mts_pairs = []
    for year in window:
        actual = _mts_or_none(year)
        if actual is None:
            continue
        mts_pairs.append((cbo_corporate_receipts(year), actual))
    window_mean_ratio = (
        (sum(p[0] for p in mts_pairs) / sum(p[1] for p in mts_pairs))
        if mts_pairs
        else None
    )

    target = live["target_10yr_billions"]

    def _err(model: float) -> float:
        return abs(model - target) / abs(target) * 100.0

    reconstruction_gap = abs(
        shipped["model_10yr_billions"] - live["model_10yr_billions"]
    )

    return {
        **live,
        "window": f"FY{window[0]}-{window[-1]}",
        "contemporaneous_vintage": CONTEMPORANEOUS_VINTAGE[policy_id],
        "contemporaneous_document": BASELINES[CONTEMPORANEOUS_VINTAGE[policy_id]][
            "document"
        ],
        "shipped_reconstruction_10yr": shipped["model_10yr_billions"],
        "shipped_reconstruction_gap": reconstruction_gap,
        "shipped_receipts_10yr": shipped["receipts_10yr_billions"],
        "contemporaneous_model_10yr": vintage["model_10yr_billions"],
        "contemporaneous_error_pct": _err(vintage["model_10yr_billions"]),
        "contemporaneous_receipts_10yr": vintage["receipts_10yr_billions"],
        "receipts_ratio_shipped_over_contemporaneous": (
            shipped["receipts_10yr_billions"] / vintage["receipts_10yr_billions"]
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
                "shipped_receipts": cbo_corporate_receipts(year),
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
    contemporaneous_mass = sum(row["contemporaneous_error_pct"] for row in rows)
    return {
        "rows": rows,
        "n": len(rows),
        "live_class_mean_pct": live_mass / len(rows),
        "live_error_mass": live_mass,
        "contemporaneous_class_mean_pct": contemporaneous_mass / len(rows),
        "contemporaneous_error_mass": contemporaneous_mass,
        "mass_reduction": live_mass - contemporaneous_mass,
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
        "Corporate +1pp Options rows — shipped path vs contemporaneous Outlook",
        "",
        f"Derived identity: Δτ × receipts × {report['base_per_dollar_of_receipts']:.5f} "
        f"× (1 − {report['offset_share']:.3f}) × §6655 phase.",
        "Shipped path: cbo_corporate_receipts() on the February 2024 block, "
        "back-extrapolated before FY2025.",
        "Contemporaneous path: BASELINES annuals already in "
        "corporate_yield_reconciliation.py, not wired into scoring.",
        "",
        f"{'row':<36} {'win':<12} {'target':>8} {'live':>8} {'err':>6} "
        f"{'contemp':>8} {'err':>6} {'1yr MTS':>8} {'err':>6}",
    ]
    for row in report["rows"]:
        lines.append(
            f"{row['policy_id']:<36} {row['window']:<12} "
            f"{row['target_10yr_billions']:8.1f} "
            f"{row['model_10yr_billions']:8.1f} "
            f"{row['error_pct']:5.1f}% "
            f"{row['contemporaneous_model_10yr']:8.1f} "
            f"{row['contemporaneous_error_pct']:5.1f}% "
            f"{_fmt(row['first_year_mts_deflated_model']):>8} "
            f"{_fmt(row['first_year_mts_deflated_error_pct'], 1):>5}%"
        )
    lines += [
        "",
        f"class mean  live {report['live_class_mean_pct']:.1f}%   "
        f"on contemporaneous paths {report['contemporaneous_class_mean_pct']:.1f}%",
        f"error mass  live {report['live_error_mass']:.1f}   "
        f"on contemporaneous paths {report['contemporaneous_error_mass']:.1f}   "
        f"reduction {report['mass_reduction']:.1f}",
        "",
        "Receipts 10-year totals (shipped vs contemporaneous) and first-year MTS",
        f"{'row':<36} {'shipped $B':>11} {'contemp $B':>11} {'ratio':>7} "
        f"{'FY1 ship':>9} {'FY1 MTS':>8} {'FY1 ×':>6}",
    ]
    for row in report["rows"]:
        lines.append(
            f"{row['policy_id']:<36} "
            f"{row['shipped_receipts_10yr']:11.1f} "
            f"{row['contemporaneous_receipts_10yr']:11.1f} "
            f"{row['receipts_ratio_shipped_over_contemporaneous']:7.3f} "
            f"{row['first_year_shipped_receipts']:9.1f} "
            f"{_fmt(row['first_year_mts_receipts']):>8} "
            f"{_fmt(row['first_year_mts_ratio'], 3):>6}"
        )
    lines += [
        "",
        "First-year MTS deflation is the R3 diagnostic; contemporaneous CBO is "
        "the quantity a lane would install. They diverge because a first-year",
        "ratio applied to a ten-year score over-deflates years that are already "
        "on the transcribed February 2024 block (2018 window) and because the",
        "September 2020 Outlook is a COVID outlier (FY2021 projected $122.8B "
        "against MTS actual $371.8B).",
    ]
    worst_gap = max(row["shipped_reconstruction_gap"] for row in report["rows"])
    lines.append(
        f"Shipped-identity reconstruction matches live scores to "
        f"${worst_gap:.3f}B (tolerance "
        f"${report['reconstruction_tolerance_billions']:.2f}B)."
    )
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
